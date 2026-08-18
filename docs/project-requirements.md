# Task Management System: Backend API Requirements

Capstone project specification for the backend learning track. This document describes the **target** system — not everything here is implemented yet.

## Table of Contents

- [1. System Overview & Objective](#1-system-overview--objective)
- [2. Tech Stack](#2-tech-stack)
- [3. Database Models (Schema)](#3-database-models-schema)
  - [User Table](#user-table)
  - [Workspace Table](#workspace-table-new)
  - [WorkspaceMember Table](#workspacemember-table-many-to-many-association-for-rbac)
  - [Task Table](#task-table)
- [4. API Endpoints & Request/Response Contracts](#4-api-endpoints--requestresponse-contracts)
  - [Authentication Endpoints](#authentication-endpoints)
  - [Workspace & Team Endpoints](#workspace--team-endpoints-new-for-rbac)
  - [Task Endpoints](#task-endpoints-protected-by-jwt--rbac)
  - [Advanced Feature Endpoints](#advanced-feature-endpoints)
- [5. Curriculum Feature Mapping](#5-curriculum-feature-mapping-the-how-to)

## **1. System Overview & Objective**

This project is a RESTful API for a Task Management System. It is designed to act as the capstone project for the backend learning track. By building this system, students will practically apply every concept from the curriculum: from Python type hints and dependency injection to database migrations, JWT authentication, background processing, Docker containerization, and advanced Role-Based Access Control (RBAC).

## **2. Tech Stack**

> * **Framework:** FastAPI  
> * **Database:** PostgreSQL  
> * **ORM:** SQLAlchemy / SQLModel  
> * **Migrations:** Alembic  
> * **Data Validation:** Pydantic V2  
> * **Authentication:** JWT (JSON Web Tokens)  
> * **Caching & Queues:** Redis  
> * **Containerization:** Docker & Docker Compose

## **3. Database Models (Schema)**

The system utilizes a relational database architecture. Students must use Alembic to generate migrations for these schemas, which include complex Many-to-Many relationships for RBAC.

### **User Table**

| Field Name | Data Type | Constraints & Details |
| :---- | :---- | :---- |
| id | UUID / Integer | Primary Key |
| email | String | Unique, Not Null, Indexed |
| hashed_password | String | Not Null |
| is_active | Boolean | Default: True |
| created_at | DateTime | Default: UTC Now |

### **Workspace Table (New)**

| Field Name | Data Type | Constraints & Details |
| :---- | :---- | :---- |
| id | UUID / Integer | Primary Key |
| name | String | Not Null, Max length 255 (e.g., "Engineering Team") |
| created_at | DateTime | Default: UTC Now |

### **WorkspaceMember Table (Many-to-Many Association for RBAC)**

| Field Name | Data Type | Constraints & Details |
| :---- | :---- | :---- |
| workspace_id | UUID / Integer | Foreign Key referencing Workspace.id, Primary Key part 1 |
| user_id | UUID / Integer | Foreign Key referencing User.id, Primary Key part 2 |
| role | String | Enum: 'owner', 'editor', 'viewer' (Not Null) |
| joined_at | DateTime | Default: UTC Now |

### **Task Table**

| Field Name | Data Type | Constraints & Details |
| :---- | :---- | :---- |
| id | UUID / Integer | Primary Key |
| title | String | Not Null, Max length 255 |
| description | Text | Nullable |
| status | String | Default: 'pending' (Enum: pending, in_progress, completed) |
| due_date | DateTime | Nullable |
| workspace_id | UUID / Integer | Foreign Key referencing Workspace.id |
| assigned_user_id | UUID / Integer | Foreign Key referencing User.id (Nullable) |
| created_at | DateTime | Default: UTC Now |
| updated_at | DateTime | On update current timestamp |

## **4. API Endpoints & Request/Response Contracts**

### **Authentication Endpoints**

> **POST /auth/register**  
  * *Request:* {"email": "user@example.com", "password": "securepassword"}  
  * *Action:* Hash password, save user, trigger background welcome email.  
  * *Response (201):* {"id": 1, "email": "user@example.com", "message": "User registered successfully"}  

> **POST /auth/login**  
  * *Request:* OAuth2PasswordRequestForm or JSON with email/password.  
  * *Action:* Verify credentials, generate JWT.

### **Workspace & Team Endpoints (New for RBAC)**

> **POST /workspaces/**  
  * *Action:* Creates a new workspace. The user who creates it is automatically added to WorkspaceMember with the 'owner' role.  

> **POST /workspaces/{workspace_id}/members**  
  * *Request:* {"user_id": 2, "role": "editor"}  
  * *Action:* Adds a user to the workspace. ONLY users with the 'owner' role can perform this action.

### **Task Endpoints (Protected by JWT & RBAC)**

> **POST /workspaces/{workspace_id}/tasks/**  
  * *Request:* {"title": "Learn FastAPI", "description": "Finish docs"}  
  * *Action:* Validates that the current user has at least the 'editor' role in this workspace before creating the task.  

> **GET /workspaces/{workspace_id}/tasks/**  
  * *Action:* Fetches tasks for a specific workspace. Validates the user has at least 'viewer' role. Uses Redis caching.  

> **PUT /workspaces/{workspace_id}/tasks/{task_id}**  
  * *Action:* Update a task. Requires 'editor' or 'owner' role. Invalidates Redis cache.  

> **DELETE /workspaces/{workspace_id}/tasks/{task_id}**  
  * *Action:* Delete task. Requires 'owner' role. Invalidates cache.

### **Advanced Feature Endpoints**

> **GET /workspaces/{workspace_id}/tasks/summary**  
  * *Action:* Aggregates task statuses for a workspace. Results are cached in Redis for 5 minutes.  

> **POST /workspaces/{workspace_id}/tasks/export**  
  * *Action:* Instant 202 Accepted. Triggers a Background Task to generate a CSV of the workspace tasks and email it to the requester.

## **5. Curriculum Feature Mapping (The "How-To")**

Students must explicitly implement the following features to pass the project requirements:

> 1. **Strict Pydantic V2 Validation:** All requests and responses modeled strictly using Pydantic.
> 2. **Role-Based Access Control (RBAC) via Dependencies:** Create advanced FastAPI dependencies to check permissions. E.g., Depends(RequireRole("editor")). This function must verify the JWT, check the database for the user's role in the requested workspace_id, and raise a 403 Forbidden if they lack permissions.  
> 3. **Many-to-Many Database Schema Design:** Effectively design and query the association table (WorkspaceMember) bridging Users and Workspaces using SQLAlchemy/SQLModel.  
> 4. **Advanced Background Tasks:** Use BackgroundTasks for sending welcome emails, notifications, and executing the heavy bulk CSV export.  
> 5. **Aggressive Redis Caching & Invalidation:** Cache the outputs of task fetches and summaries. Invalidate specific workspace cache keys upon task mutation.  
> 6. **Rate Limiting:** Protect authentication endpoints from brute-force attacks using Redis.  
> 7. **Dockerization:** Containerize the FastAPI app, PostgreSQL database, and Redis instance using docker-compose.yml.
