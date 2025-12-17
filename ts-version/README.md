# AgentCore Gateway Tools API - TypeScript/NestJS Version

A TypeScript/NestJS port of the Python FastAPI project for managing AWS AgentCore Gateway and tools/targets.

## Project Structure

```
ts-version/
├── src/
│   ├── main.ts                          # Application entry point
│   ├── app.module.ts                    # Root NestJS module
│   ├── api/
│   │   ├── app.controller.ts            # HTTP endpoints
│   │   ├── dtos/
│   │   │   └── index.ts                 # Request/Response DTOs
│   │   └── validations/
│   │       └── validations.service.ts   # Input validation logic
│   └── services/                        # Core business logic (injectable, reusable)
│       ├── services.module.ts           # Services module
│       ├── credentials/
│       │   └── credentials.service.ts   # Credential provider management
│       ├── s3/
│       │   └── s3.service.ts            # S3 operations for OpenAPI specs
│       ├── gateways/
│       │   └── gateway.service.ts       # Gateway CRUD operations
│       ├── tools/
│       │   └── tools.service.ts         # Target/Tool CRUD operations
│       └── openapi-generator/
│           └── openapi-generator.service.ts  # OpenAPI spec generation
├── dist/                                # Compiled JavaScript (generated)
├── .env                                 # Environment configuration
├── tsconfig.json                        # TypeScript configuration
├── package.json                         # Dependencies and scripts
└── README.md                            # This file
```

## Services Layer (Decoupled & Injectable)

All services are NestJS-injectable and completely decoupled from the controller layer. This means you can:
- Copy any service into another NestJS project
- Test services independently
- Inject them into other modules/services
- Reuse them without the API layer

### Available Services

1. **CredentialsService**
   - `createOrGetApiKeyCredentialProvider(name, apiKey)` - Create/retrieve credential providers

2. **S3Service**
   - `uploadOpenApiSpec(spec, toolName, gatewayId, bucketName?)` - Upload specs to S3

3. **GatewayService**
   - `createGateway(name, roleArn, isAuthenticated, authConfig?, description?)`
   - `getGateway(gatewayId)`
   - `listGateways(maxResults?, nextToken?)`
   - `updateGateway(gatewayId, name, protocolType, authorizerType, roleArn, ...)`
   - `deleteGateway(gatewayId)`
   - `createAgentCoreGatewayRole(roleName)` - Create IAM role

4. **ToolsService**
   - `createGatewayTarget(gatewayId, targetName, openApiS3Uri, credentialProviderArn, ...)`
   - `getGatewayTarget(gatewayId, targetId)`
   - `listGatewayTargets(gatewayId, maxResults?, nextToken?)`
   - `updateGatewayTarget(gatewayId, targetId, targetName, targetConfiguration, ...)`
   - `deleteGatewayTarget(gatewayId, targetId)`

5. **OpenApiGeneratorService**
   - `generateOpenApiSpec(toolName, method, url, queryParams?, headers?, bodySchema?, description?)`

6. **ValidationsService**
   - `validateAuth(auth?)` - Validate authentication configuration
   - `validateOpenApiSpec(spec)` - Validate OpenAPI spec structure

## Setup & Running

### Prerequisites
- Node.js 18+ (with npm)
- AWS credentials configured (via `~/.aws/credentials` or environment variables)
- AWS permissions for Bedrock AgentCore, IAM, and S3

### Installation

```bash
cd ts-version
npm install
```

### Configuration

Edit `.env` with your AWS settings:

```env
AWS_DEFAULT_REGION=us-east-1
PORT=3000
NODE_ENV=development
OPENAPI_SPECS_BUCKET=agentcore-gateway-openapi-specs-bucket
```

### Build

```bash
npm run build
```

Outputs compiled JavaScript to `dist/` directory.

### Run

**Development (with auto-reload):**
```bash
npm run dev
```

**Production (from compiled dist):**
```bash
npm start
```

The API will start on `http://localhost:3000`

## API Endpoints

### Health Check
- `GET /health` - Server health check

### Gateway Management
- `GET /gateways` - List all gateways
- `POST /gateways` - Create gateway with auth
- `POST /gateways/no-auth` - Create gateway without auth
- `GET /gateways/:gateway_id` - Get gateway details
- `PUT /gateways/:gateway_id` - Update gateway
- `DELETE /gateways/:gateway_id` - Delete gateway

### Tools/Targets Management
- `GET /gateways/:gateway_id/tools` - List tools for gateway
- `POST /tools/from-url` - Create tool from OpenAPI URL
- `POST /tools/from-spec` - Create tool from inline OpenAPI spec
- `POST /tools/from-api-info` - Create tool from manual API info
- `GET /gateways/:gateway_id/tools/:target_id` - Get tool details
- `PUT /gateways/:gateway_id/tools/:target_id` - Update tool
- `DELETE /gateways/:gateway_id/tools/:target_id` - Delete tool

## Differences from Python Version

1. **Error Handling**: Uses NestJS HttpException instead of FastAPI HTTPException
2. **Async/Await**: All async operations use native promises
3. **Logging**: Uses NestJS Logger instead of print statements
4. **AWS SDK**: Uses AWS SDK v3 instead of boto3
5. **Type Safety**: Full TypeScript types for all AWS responses

## Performance Notes

- AWS SDK v3 is promise-based and efficient
- S3 bucket operations are cached within session
- All AWS clients are instantiated per-call (can be optimized with singleton if needed)

## Testing Against Python Version

To verify compatibility:

1. Start both servers on different ports
2. Run same requests against both
3. Compare response structures and status codes
4. Python: `python main.py` (runs on port 8000)
5. TypeScript: `npm run dev` (runs on port 3000)

## Next Steps

- Add request/response logging middleware
- Add metrics collection (CloudWatch integration)
- Add retry logic for AWS SDK calls
- Add environment-specific configurations
- Add integration tests
lly