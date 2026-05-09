# **Project Axiom: Autonomous BI Engine (v2.0)**

**Technical Specification for Agentic Data Analysis & Multi-Format Reporting**

## **1\. Project Overview**

Project Axiom is an agentic framework designed to transform raw datasets (CSV, Excel, SQL Databases) into a full suite of professional assets: clean data, analytical reports (PDF), executive presentations (PPTX), and automated dashboards (Excel/Power BI). Unlike traditional BI, Axiom uses a **self-correcting reasoning loop** to handle data anomalies and "multi-hop" exploratory analysis.

## **2\. Core Architecture (The Agentic Brain)**

The system utilizes a **Stateful Graph** (via LangGraph) to allow for iterative reasoning and error recovery:

* **Orchestrator (The Router):** Analyzes user intent and maintains the "Shared State" (the conversation history and data manifesto).  
* **Data Engineer Agent:** Performs schema detection, cleaning, and type-casting. It builds the "Source of Truth" for other agents.  
* **Analyst Agent (ReAct Loop):** Operates inside a **Stateful Code Sandbox**. It writes Python, executes it, observes the output/errors, and iterates until the analysis is valid.  
* **Document Architect Agent:** Compiles validated insights into final presentation formats (PDF, PPTX, XLSX).

## **3\. Updated Tech Stack Requirements**

* **Orchestration:** LangGraph (Required for stateful cycles and "human-in-the-loop" approval).  
* **Code Execution (Sandbox):** \* *Option A (Production):* **E2B** (Cloud-hosted, stateful Python sandboxes).  
  * *Option B (Self-Hosted):* **Docker-based Python Interpreter** with restricted networking.  
* **Analysis:** DuckDB (for fast SQL on local files), Pandas, Statsmodels.  
* **Visualization:** Plotly (for interactive HTML artifacts) and Seaborn (for static PDF/PPTX embeds).  
* **Document Generation:** fpdf2, python-pptx, XlsxWriter.

## **4\. Refined Agentic Workflow**

### **Step 1: Recursive Ingestion & Profiling**

* **Action:** Data Engineer Agent runs a "Read-Only" probe.  
* **State Update:** Creates a Data Manifesto containing:  
  * Strict Schema (Column types, Null counts).  
  * Semantic Metadata (e.g., "The 'revenue' column represents USD").  
  * Anomaly Warnings (e.g., "Outliers detected in Q2 sales").

### **Step 2: Stateful Insight Mining (The Loop)**

* **The ReAct Cycle:**  
  1. **Reason:** "I need to check if churn correlates with the new checkout UI rollout."  
  2. **Act:** Agent writes Python code to merge churn\_logs and ui\_rollout\_dates.  
  3. **Observe (Sandbox):** Returns a KeyError because the date formats don't match.  
  4. **Correct:** Agent catches the error, adjusts the pd.to\_datetime parameters, and re-executes.  
* **Output:** Validated summary\_stats.json and high-resolution chart assets.

### **Step 3: Multi-Format Rendering & Cross-Check**

* **Verification Node:** Before finalizing, a "Auditor" agent verifies that the KPI values in the PDF match the calculations in the Excel dashboard.  
* **Rendering:** \* **PDF:** Narrative summary \+ charts.  
  * **PPTX:** "One insight per slide" format.  
  * **Excel:** Formatted tables with native conditional formatting.

## **5\. Security & Sandbox Guardrails**

1. **Network Isolation:** The Code Sandbox (E2B/Docker) must have no internet access to prevent data exfiltration.  
2. **Stateful Persistence:** The sandbox must persist its environment between turns so the agent doesn't have to re-load 1GB datasets every time it asks a follow-up question.  
3. **Read-Only Database Access:** SQL-based sources must use a restricted user profile (SELECT only).

## **6\. File Structure & Output Management**

/axiom\_output/

├── \[run\_id\]/

│ ├── report.pdf

│ ├── slide\_deck.pptx

│ ├── raw\_data\_dashboard.xlsx

│ ├── /sandbox\_logs/ (Trace of all code executed)

│ └── /assets/ (Original .png and .json files)

## **7\. Human-in-the-Loop (HITL) Checkpoints**

* **Checkpoint 1:** Orchestrator must get user approval on the "Analysis Plan" before executing heavy compute/sandbox runs.  
* **Checkpoint 2:** Final review of the PDF "Executive Summary" before the PPTX and Power BI refreshes are triggered.