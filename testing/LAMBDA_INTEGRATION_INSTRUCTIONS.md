# Lambda Integration Instructions

## Overview
Integrate the gateway and tools services from this POC into the existing Lambda. The Lambda will serve as a registry storing metadata in DynamoDB while maintaining sync with AgentCore Gateway.

## Architecture Pattern

### Safe CRUD Flow (Order Matters)

**CREATE:**
1. Validate request
2. **Store to DynamoDB** with status `PENDING`
3. Create in AgentCore Gateway
4. **Update DynamoDB** with status `ACTIVE` + gateway IDs/timestamps
5. Return success to caller

**UPDATE:**
1. Validate request
2. Check existing record in DynamoDB
3. Update in AgentCore Gateway
4. Update metadata in DynamoDB
5. Return success

**DELETE:**
1. Check DynamoDB for record
2. Set status to `DELETING` in DynamoDB
3. Delete from AgentCore Gateway
4. Delete from DynamoDB (or mark as `DELETED` for audit)
5. Return success

## Implementation Steps

### Phase 1: Setup
- [ ] Copy service modules from POC into Lambda codebase:
  - `services/gateway/gateway_service.py`
  - `services/tools/tools_service.py`
  - `services/credentials/credentials_service.py`
  - `services/openapi_generator/openapi_generator.py`
  - `services/s3/s3_service.py`
- [ ] Update Lambda dependencies (boto3, requests, pydantic, etc.)
- [ ] Create DynamoDB tables for gateways and tools (with status field)

### Phase 2: DynamoDB Schema
Create two tables:
- **Gateways Table**: gateway_id (PK), status (PENDING|ACTIVE|DELETING|FAILED), agentcore_gateway_id, metadata, synced_at, etc.
- **Tools Table**: tool_id (PK), gateway_id (SK), status (PENDING|ACTIVE|DELETING|FAILED), agentcore_target_id, metadata, synced_at, etc.

Include fields for: created_by, team, timestamps, request_id (for idempotency)

### Phase 3: Lambda Handlers
Implement handlers following the safe CRUD flow:
- `create_gateway()` - implement CREATE flow
- `get_gateway()` - fetch from DynamoDB
- `update_gateway()` - implement UPDATE flow
- `delete_gateway()` - implement DELETE flow
- `create_tool()` - implement CREATE flow (supports file upload, URL, API info, spec)
- `get_tool()` - fetch from DynamoDB
- `update_tool()` - implement UPDATE flow
- `delete_tool()` - implement DELETE flow

### Phase 4: Error Handling & Sync
- [ ] Implement try-catch with proper rollback logic
- [ ] Add request ID validation for idempotency
- [ ] Log failures with error details to DynamoDB
- [ ] Create reconciliation function (optional for Phase 2+)

### Phase 5: Integration Tests
- [ ] Manual test: Create gateway, verify DynamoDB + AgentCore both have data
- [ ] Manual test: Delete gateway, verify both systems cleaned up
- [ ] Manual test: Simulate AgentCore failure, verify DynamoDB shows PENDING state

## Key Guidelines

✅ **DO:**
- Write to DynamoDB first (before AgentCore) on CREATE
- Store status field to track operation state
- Include request IDs for idempotency
- Log all operations for audit trail
- Return both DynamoDB metadata + AgentCore info in responses

❌ **DON'T:**
- Assume operations succeed without checking responses
- Skip DynamoDB writes to simplify flow
- Write documentation or tests yet
- Make up error handling logic

## Questions?
If anything is unclear or contradicts existing Lambda patterns, **ask first** before implementing. Don't assume or make up solutions.

## Work Tracking
Create a TODO file in the Lambda project and track:
- [ ] Each phase completion
- [ ] Each handler implementation
- [ ] Testing checklist
- [ ] Known issues or blockers

This ensures visibility and lets you track progress.

