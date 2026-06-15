from pydantic import BaseModel, Field
from typing import Literal
from agents import Agent, Runner
from dotenv import load_dotenv
from agents.mcp import MCPServerStdio
import asyncio
import json

load_dotenv()


class JobRequirements(BaseModel):
    job_title: str
    seniority: Literal["junior", "middle", "senior"]
    years_experience: int
    must_have_skills: list[str]
    nice_to_have_skills: list[str]
    responsibilities: list[str]


class GapAnalysis(BaseModel):
    matched_skills: list[str]
    missing_skills: list[str]
    coverage_score: float = Field(ge=0.0, le=1.0)
    verdict: str
    interview_focus: list[str]


class CoverLetter(BaseModel):
    greeting: str
    body: str
    closing: str
    full_text: str


# Converts structured AI outputs (JobRequirements + GapAnalysis)
# into a Markdown report that will be uploaded to Google Drive.
def build_markdown_report(jd: JobRequirements, gap: GapAnalysis) -> str:
    matched_md = "\n".join(f"- {item}" for item in gap.matched_skills)
    missing_md = "\n".join(f"- {item}" for item in gap.missing_skills)
    focus_md = "\n".join(f"- {item}" for item in gap.interview_focus)
    must_have_md = "\n".join(f"- {item}" for item in jd.must_have_skills)
    nice_to_have_md = "\n".join(f"- {item}" for item in jd.nice_to_have_skills)
    responsibilities_md = "\n".join(f"- {item}" for item in jd.responsibilities)

    return f"""# Resume Gap Analysis Report

## Job Info
- Title: {jd.job_title}
- Seniority: {jd.seniority}
- Years experience: {jd.years_experience}

## Coverage Score
{gap.coverage_score:.0%}

## Must Have Skills
{must_have_md}

## Nice To Have Skills
{nice_to_have_md}

## Responsibilities
{responsibilities_md}

## Matched Skills
{matched_md}

## Missing Skills
{missing_md}

## Verdict
{gap.verdict}

## Interview Focus
{focus_md}
"""


# Processes a single vacancy:
# 1. Analyze job description
# 2. Compare resume against requirements
# 3. Generate cover letter
# 4. Upload results to Google Drive
async def process_one_job(job, resume_text, analyst_agent, reviewer_agent, cover_letter_agent, drive_server,
                          semaphore) -> str:
    # Starts the external MCP server and exposes Google Drive tools
    # to agents and pipeline code.
    async with semaphore:
        job_filename = job["name"]
        try:
            analyst_result = await Runner.run(analyst_agent,
                                              f"Find the file '{job_filename}' in the 'jobs' folder and analyze it.")
            jd = analyst_result.final_output
            reviewer_prompt = f"Job requirements:\n{jd.model_dump_json(indent=2)}\n\n" f"Resume content: {resume_text}"
            reviewer_result = await Runner.run(reviewer_agent, reviewer_prompt)
            gap = reviewer_result.final_output
            cover_letter_prompt = (
                f"Job requirements:\n{jd.model_dump_json(indent=2)}\n\n"
                f"Gap analysis:\n{gap.model_dump_json(indent=2)}\n\n"
                f"Resume content: {resume_text}\n\n"
                f"Write a tailored cover letter."
            )

            cover_letter_result = await Runner.run(cover_letter_agent, cover_letter_prompt)
            cover_letter = cover_letter_result.final_output
            report = build_markdown_report(jd, gap)
            await drive_server.call_tool(
                "upload_file_to_folder",
                {
                    "folder_name": "tailored",
                    "filename": job_filename.replace(".txt", "_analysis.md"),
                    "content": report
                }
            )

            await drive_server.call_tool(
                "upload_file_to_folder",
                {
                    "folder_name": "tailored",
                    "filename": job_filename.replace(".txt", "_cover_letter.md"),
                    "content": cover_letter.full_text
                }
            )

            return f"✓ {job_filename}"
        except Exception as e:
            return f"✗ {job_filename}: {e}"


async def main() -> None:
    semaphore = asyncio.Semaphore(1)
    async with MCPServerStdio(
            name="drive",
            params={"command": "python", "args": ["drive_mcp_server.py"]},
    ) as drive_server:
        jobs_response = await drive_server.call_tool("list_files_in_folder", {"folder_name": "jobs"})
        jobs = [json.loads(item.text) for item in jobs_response.content]

        # Agent 1: extracts structured requirements from a job description.
        reviewer_agent = Agent(
            name="Resume Reviewer",
            instructions="""You are a strict career reviewer. You receive job requirements AND the full resume text directly in the user message.
    
                Steps you MUST follow:
                1. Read the provided job requirements.
                2. Read the provided resume text.
                3. Compare the resume against the job requirements.
                4. Return a strict and honest GapAnalysis.
    
                coverage_score MUST be between 0.0 and 1.0 where 0.0 = no match and 1.0 = perfect match.
                Do NOT invent content.""",
            output_type=GapAnalysis
        )

        # Agent 2: performs resume-to-job gap analysis.
        analyst_agent = Agent(
            name="Job Analyst",
            mcp_servers=[drive_server],
            instructions="""You are a recruiter assistant. Your goal is to analyze a job description stored in Google Drive.
    
                Steps you MUST follow:
                1. Call list_files_in_folder('jobs') to get all available job files.
                2. From the returned list, find the file matching the name provided in the user message.
                3. Call read_drive_file(file_id) with that file's ID to fetch its content.
                4. Extract structured job requirements as JobRequirements.
    
                Do NOT invent content. Always use the tools to read real files.""",
            output_type=JobRequirements
        )

        # Agent 3: generates a personalized cover letter.
        cover_letter_agent = Agent(
            name="Cover Letter",
            instructions="""You are a professional career writer. Your goal is to write a personalized cover letter for a specific job application. You receive job requirements, gap analysis, AND the full resume text in the message.

                Steps you MUST follow:
                1. Read the provided job requirements.
                2. Read the provided gap analysis.
                3. Read the provided resume text.
                4. Write a personalized cover letter tailored to the target job.
                5. Highlight relevant matched skills and experiences from the resume.
                6. Do NOT claim skills, experience, certifications, or achievements that are not present in the resume.
                7. If there are missing skills, do not lie about having them. Instead, emphasize motivation, ability to learn quickly, academic background, personal projects, and willingness to develop those skills.
                8. Keep the tone professional, confident, and positive.
                9. The cover letter must be between 150 and 250 words.
        
                Output only the final cover letter text.
                Do NOT invent content.""",
            output_type=CoverLetter
        )

        resume_filename = input("Write the name of the file for the scanned resume: ")
        # Read the resume once and reuse its content for all jobs.
        root_response = await drive_server.call_tool("list_files_in_folder", {"folder_name": "ResumeTailor"})
        files = [json.loads(item.text) for item in root_response.content]
        resume_id = next(f["id"] for f in files if f["name"] == resume_filename)
        resume_response = await drive_server.call_tool("read_drive_file", {"file_id": resume_id})
        resume_text = resume_response.content[0].text
        # Create one processing task per job vacancy.
        tasks = [process_one_job(job, resume_text, analyst_agent, reviewer_agent, cover_letter_agent, drive_server,
                                 semaphore) for job in jobs]
        # Wait until all job processing tasks are completed.
        results = await asyncio.gather(*tasks)
        success = [r for r in results if r.startswith("✓")]
        failed = [r for r in results if r.startswith("✗")]
        print(f"Done. Success: {len(success)}, Failed: {len(failed)}")
        for result in results:
            print(result)


if __name__ == '__main__':
    asyncio.run(main())
