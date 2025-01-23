import streamlit as st
from jira import JIRA
from transformers import pipeline


st.title("JIRA Query Assistant Bot (LLM-Powered)")


st.sidebar.header("Configuration")
jira_url = st.sidebar.text_input("JIRA URL")
jira_email = st.sidebar.text_input("JIRA Email")
jira_token = st.sidebar.text_input("JIRA API Token")

@st.cache_resource
def initialize_jira(jira_url, jira_email, jira_token):
    try:
        jira = JIRA(server=jira_url, basic_auth=(jira_email, jira_token))
        st.success("Connected to JIRA successfully!")
        return jira
    except Exception as e:
        st.error(f"Failed to connect to JIRA: {e}")
        return None


@st.cache_resource
def load_llm_model():
    try:
        st.info("Loading the LLM Model...")
        model = pipeline("text2text-generation", model="t5-small")  
        st.success("LLM Model Loaded Successfully!")
        return model
    except Exception as e:
        st.error(f"Failed to load model: {e}")
        return None


model = load_llm_model()
jira = initialize_jira(jira_url, jira_email, jira_token)

step_3_completed = False

if jira and model:
    st.subheader("Step 1: Ask your query")
    user_query = st.text_input("Enter your query:", placeholder="e.g., How many priority tickets are raised today?")

    if user_query:
        
        st.write("**Translating query to JQL...**")
        jql_prompt = (
                    f"Translate the following natural language query into a valid JIRA Query Language (JQL) command. "
                    f"Ensure the query uses correct JQL syntax, such as 'project = XYZ' or 'priority = High':\n"
                    f"Query: {user_query}\n"
                )
        llm_response = model(jql_prompt, max_length=50)
        jql_query = llm_response[0]['generated_text'].strip()
        st.write(f"Generated JQL: `{jql_query}`")

        
        if "project" in user_query.lower() and "project =" not in jql_query:
            st.write("**Fetching list of projects from JIRA...**")
            try:
                projects = jira.projects()
                project_names = [project.name for project in projects]
                st.info("Please confirm the project name:")
                selected_project = st.selectbox("Select a project:", project_names)

                if selected_project:
                   
                    jql_query += f' AND project = "{selected_project}"'
                    st.success(f"Updated JQL: `{jql_query}`")

                   
                    st.subheader("Step 3: Execute the Command")
                    confirm_query = st.text_input(
                        "You can refine or confirm your query:",
                        value=f"I need tickets from project {selected_project}",
                    )
                    
                    if st.button("Execute Command"):
                        
                        execute_prompt = f"Translate this query to a JQL command: {confirm_query}"
                        jql_final_response = model(execute_prompt, max_length=50)
                        final_jql = jql_final_response[0]['generated_text'].strip()
                        st.write(f"Executing Final JQL: `{final_jql}`")

                        
                        try:
                            issues = jira.search_issues(final_jql)
                            if issues:
                                st.success(f"Found {len(issues)} priority tickets:")
                                for issue in issues:
                                    st.write(f"- **{issue.key}**: {issue.fields.summary}")

                                step_3_completed = True

                            else:
                                st.warning("No tickets found for the specified query.")
                        except Exception as e:
                            st.error(f"Error executing final JQL query: {e}")
            except Exception as e:
                st.error(f"Error fetching projects: {e}")

if step_3_completed and jira and model: 
    st.subheader("Step 4: Final Response")
    st.write("**Translating fetched results into natural language...**")

    if "project =" not in jql_query:
       
        if "selected_project" in locals():
            jql_query += f' AND project = "{selected_project}"'
            st.success(f"Updated JQL: `{jql_query}`")
        else:
            st.error("Project not specified or incorrectly formatted in the query.")
            st.stop()  

    
    try:
        issues = jira.search_issues(final_jql)  

        if issues:
            project_name = selected_project if 'selected_project' in locals() else "specified project"
            issue_count = len(issues)

            
            st.success(f"There are {issue_count} tickets raised today for {project_name}.")

        else:
            st.warning(f"No tickets found for the query in {project_names}.")
    except Exception as e:
        st.error(f"Error fetching or summarizing results: {e}")
