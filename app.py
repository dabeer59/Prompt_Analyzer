import streamlit as st
import pandas as pd
import google.generativeai as genai
import time

# Constants
API_KEY = 'AIzaSyARzO7JWAa5EpwqO3x87Vs1FI2SaCxpBq0'  # Replace with your actual API key
SYSTEM_INSTRUCTIONS = (
    'You are an expert chatbot evaluator. '
    'Categorize the given prompts as "Good" or "Bad" based on clarity, effectiveness, and relevance. '
    'Provide brief feedback for each prompt.'
)

# Streamlit app
st.title("Detailed Prompt Feedback Analysis with Gemini")

# File upload
uploaded_file = st.file_uploader("Upload a CSV or Excel file with prompts", type=["csv", "xlsx"])

if uploaded_file is not None:
    # Read the Excel/CSV file
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    # Check for necessary columns
    required_columns = {'Prompt', 'Agent ID', 'Agent Name', 'Team Leader', 'Manager'}
    if not required_columns.issubset(df.columns):
        st.error(f"The uploaded file must contain the following columns: {', '.join(required_columns)}")
    else:
        st.write("Prompts to analyze:")
        st.dataframe(df)

        # Initialize columns for analysis results if not present
        if 'Category' not in df.columns:
            df['Category'] = ""
        if 'Feedback' not in df.columns:
            df['Feedback'] = ""

        # Batch size control
        batch_size = st.number_input("Number of prompts to analyze in this session", min_value=1, max_value=len(df), value=20)

        # Analyze button
        if st.button("Analyze Prompts"):
            # Configure Gemini API
            genai.configure(api_key=API_KEY)

            quota_exhausted = False  # Flag to stop if quota is exhausted

            # Process prompts up to the specified batch size
            processed_count = 0
            for idx, prompt in enumerate(df['Prompt']):
                if processed_count >= batch_size:
                    break  # Process only up to the batch size limit

                # Skip already analyzed prompts
                if df.at[idx, 'Category'] != "":
                    continue

                # Construct prompt for Gemini
                detailed_prompt = (
                    f"Prompt: '{prompt}'\n"
                    "Is this prompt 'Good' or 'Bad' based on clarity, relevance, and effectiveness? "
                    "Provide feedback on why it is categorized as such."
                )

                try:
                    # Call Gemini model for each prompt
                    model = genai.GenerativeModel(
                        model_name="gemini-1.5-flash",
                        system_instruction=SYSTEM_INSTRUCTIONS
                    )
                    response = model.generate_content(detailed_prompt)
                    response_message = response.text.strip()

                    # Process response to extract category and feedback
                    if "Good" in response_message:
                        df.at[idx, 'Category'] = "Good"
                    else:
                        df.at[idx, 'Category'] = "Bad"

                    feedback_start = response_message.find("Feedback:")
                    df.at[idx, 'Feedback'] = response_message[feedback_start + len("Feedback: "):].strip()

                    # Delay to avoid hitting API limits
                    time.sleep(1)  # Adjust delay as needed based on rate limits
                    processed_count += 1

                except Exception as e:
                    if "429" in str(e):
                        st.warning("API quota has been exhausted. Stopping further analysis to avoid errors.")
                        quota_exhausted = True
                        break  # Stop further requests to avoid continuous quota errors
                    else:
                        st.error(f"Error analyzing prompt at row {idx + 1}: {str(e)}")

            # Save partially analyzed results for future sessions
            df.to_csv("analyzed_prompts.csv", index=False)

            # Display detailed feedback for each prompt
            st.write("### Detailed Feedback for Each Prompt:")
            st.dataframe(df[['Agent ID', 'Agent Name', 'Prompt', 'Category', 'Feedback']])

            # Inform if the analysis stopped due to quota limit
            if quota_exhausted:
                st.info("Partial analysis completed due to API quota exhaustion. Please review results below.")
