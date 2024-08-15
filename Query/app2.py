import os
import fitz  # PyMuPDF
from openai import OpenAI
import re
import streamlit as st
from docx import Document
from dotenv import load_dotenv
import time

load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ''
    for page in doc:
        text += page.get_text()
    return text

# Function to extract text from Word document
def extract_text_from_docx(docx_path):
    doc = Document(docx_path)
    return '\n'.join([para.text for para in doc.paragraphs])

# Function to load and parse resumes
def load_resumes(folder_path):
    resumes = {}
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if filename.endswith('.pdf'):
            resumes[filename] = extract_text_from_pdf(file_path)
        elif filename.endswith('.docx'):
            resumes[filename] = extract_text_from_docx(file_path)
    return resumes

# Function to extract the number of resumes requested from the query
def extract_num_resumes(query):
    match = re.search(r'\btop (\d+)\b', query, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 3  # Default to 3 if no specific number is mentioned

# Implement rate limiting
def rate_limit():
    time.sleep(1)  # Wait for 1 second between API calls

def query_resumes(query, resumes, num_resumes):
    prompt = f"""Analyze the following resumes based on this job description and requirements: '{query}'
     Pay special attention to career patterns, skills, and experience that match the query.
    For each resume, carefully examine the work history:
    1. Identify all companies the candidate has worked for.
    2. Calculate the duration of employment at each company.
    3. Determine the total number of companies and the average tenure.
    4. Assess if the candidate has a pattern of frequent job changes (e.g., multiple jobs lasting less than 2 years).

    Provide a detailed analysis for each resume, including:
    2. A summary of the candidate's work history, including the number of companies and average tenure.
    3. An assessment of whether the candidate frequently changes jobs, based on their work history.
    4. A brief explanation (max 50 words) of why the resume matches or doesn't match the query.

    Then, list the top {num_resumes} most relevant resumes by filename, score, work history summary, and explanation.
    
    Job Description: {query}

    Resumes:
    """
    
    for filename, content in resumes.items():
        prompt += f"\nFilename: {filename}\nContent: {content[:2000]}...\n"  # Increased to first 2000 characters

    try:
        rate_limit()
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an HR assistant analyzing resumes. Provide detailed analysis of work history and job change patterns for each resume."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,  # Increased token limit
            temperature=0.7
        )
        
        return completion.choices[0].message.content.strip()

    except Exception as e:
        print(f"Error occurred: {e}. Retrying in 5 seconds...")
        time.sleep(5)
        return query_resumes(query, resumes, num_resumes)

# Streamlit UI
def main():
    st.title("HR Resume Matcher")
    st.write("Input the job description and requirements:")

    query = st.text_area("Job Description / Query", height=200)
    resume_folder = r'C:\Users\Gautam\Desktop\QUERY\Query\Resumes'

    if st.button("Find Resumes"):
        if query:
            num_resumes = extract_num_resumes(query)
            resumes = load_resumes(resume_folder)
            
            with st.spinner('Analyzing resumes...'):
                response = query_resumes(query, resumes, num_resumes)

            st.subheader("Resume Analysis Results")
            st.text_area("Full Analysis", response, height=400)

            # Extract and display top resumes
            top_resumes = re.findall(r'\d+\.\s+(.*?):.*?Score:\s+(\d+).*?Work History:\s+(.*?)Explanation:\s+(.*?)(?=\n\d+\.|$)', response, re.DOTALL)
            
            st.subheader(f"Top {num_resumes} Matching Resumes")
            for i, (filename, score, work_history, explanation) in enumerate(top_resumes[:num_resumes], 1):
                st.write(f"{i}. {filename.strip()} (Score: {score})")
                st.write(f"   Work History: {work_history.strip()}")
                st.write(f"   Explanation: {explanation.strip()}")
                st.write("---")
        else:
            st.warning("Please enter a job description or query.")

if __name__ == "__main__":
    main()