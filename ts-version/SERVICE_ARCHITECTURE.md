# Service Architecture & Dependency Graph

## Decoupled Services Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     HTTP Endpoints                              │
│                  (app.controller.ts)                            │
│  GET /health, POST /gateways, GET /tools, DELETE /tools, ...  │
└──┬──────────────────────────────────────────────────────────┬──┘
   │                                                            │
   ├─────────────────────┬────────────────────────────────────┤
   │                     │                                    │
   ▼                     ▼                                    ▼
┌─────────────┐  ┌──────────────┐                   ┌──────────────┐
│  Validation │  │  Orchestration Logic │           │  Pure Services    
│  Service    │  │  (in controller)     │           │  (injectable) 
└─────────────┘  └──────────────┴──────┬────────────┴──────────────┘
                                       │
                  ┌────────────────────┼────────────────────┐
                  │                    │                    │
                  ▼                    ▼                    ▼
            ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
            │  Credentials │    │  S3 Service  │    │  Gateway     │
            │  Service     │    │              │    │  Service     │
            └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
                   │                   │                   │
                   │     AWS SDK v3    │                   │
                   │     Clients       │                   │
                   ▼                   ▼                   ▼
            ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
            │ BedrockAgent │    │ S3 Client    │    │ BedrockAgent │
            │ CoreControl  │    │ STS Client   │    │ CoreControl  │
            │ Client       │    └──────────────┘    │ IAM Client   │
            └──────────────┘                        └──────────────┘
                   │                                       │
                   └───────────────┬───────────────────────┘
                                   │
                                   ▼
                            ┌─────────────┐
                            │ AWS Account │
                            └─────────────┘
```

## Service Definitions

### 1. ValidationsService
**Purpose**: Validate input before processing
**Methods**:
- `validateAuth(auth?)` - Check authentication config
- `validateOpenApiSpec(spec)` - Check OpenAPI format

**No dependencies** - Standalone utility

```typescript
// Example usage
const validationsService = new ValidationsService();
validationsService.validateAuth(authDto);
```

### 2. CredentialsService
**Purpose**: Manage API key credential providers in AWS
**Methods**:
- `createOrGetApiKeyCredentialProvider(name, apiKey)`

**Dependencies**: 
- AWS: BedrockAgentCoreControlClient
- Env: AWS_DEFAULT_REGION

```typescript
// Example usage
const credService = new CredentialsService();
const arn = await credService.createOrGetApiKeyCredentialProvider(
  'my-provider', 
  'api-key-value'
);
```

### 3. S3Service
**Purpose**: Store and manage OpenAPI specs in S3
**Methods**:
- `uploadOpenApiSpec(spec, toolName, gatewayId, bucketName?)`

**Dependencies**:
- AWS: S3Client, STSClient
- Env: AWS_DEFAULT_REGION

```typescript
// Example usage
const s3Service = new S3Service();
const s3Uri = await s3Service.uploadOpenApiSpec(
  openApiSpec,
  'my-tool',
  'gateway-123'
);
// Returns: s3://bucket/gateways/gateway-123/tools/my-tool/timestamp-uuid.json
```

### 4. GatewayService
**Purpose**: Manage gateway lifecycle
**Methods**:
- `createGateway(name, roleArn, isAuthenticated, authConfig?, description?)`
- `getGateway(gatewayId)`
- `listGateways(maxResults?, nextToken?)`
- `updateGateway(gatewayId, name, protocol, authType, roleArn, description?, config?)`
- `deleteGateway(gatewayId)`
- `createAgentCoreGatewayRole(roleName)`

**Dependencies**:
- AWS: BedrockAgentCoreControlClient, IAMClient
- Env: AWS_DEFAULT_REGION

```typescript
// Example usage
const gatewayService = new GatewayService();

// Create IAM role
const roleArn = await gatewayService.createAgentCoreGatewayRole(
  'sample-lambdagateway-role-demo'
);

// Create gateway without auth
const gateway = await gatewayService.createGateway(
  'my-gateway',
  roleArn,
  false
);
```

### 5. ToolsService
**Purpose**: Manage gateway targets (tools)
**Methods**:
- `createGatewayTarget(gatewayId, targetName, openApiS3Uri, credentialProviderArn, ...)`
- `getGatewayTarget(gatewayId, targetId)`
- `listGatewayTargets(gatewayId, maxResults?, nextToken?)`
- `updateGatewayTarget(gatewayId, targetId, targetName, targetConfiguration, ...)`
- `deleteGatewayTarget(gatewayId, targetId)`

**Dependencies**:
- AWS: BedrockAgentCoreControlClient
- Env: AWS_DEFAULT_REGION

```typescript
// Example usage
const toolsService = new ToolsService();

const tool = await toolsService.createGatewayTarget(
  'gateway-123',
  'my-tool',
  's3://bucket/spec.json',
  'arn:aws:bedrock:...', // credential provider ARN
  'api_key',              // param name
  'QUERY_PARAMETER'       // location
);
```

### 6. OpenApiGeneratorService
**Purpose**: Generate OpenAPI specs from manual API info
**Methods**:
- `generateOpenApiSpec(toolName, method, url, queryParams?, headers?, bodySchema?, description?)`

**No dependencies** - Pure generation logic

```typescript
// Example usage
const generatorService = new OpenApiGeneratorService();

const spec = generatorService.generateOpenApiSpec(
  'my-todo-api',
  'GET',
  'https://api.example.com/todos',
  { id: { type: 'number' } },  // query params
  { Authorization: { type: 'string' } }, // headers
  undefined,
  'Get all todos'
);
```

## Data Flow Examples

### Example 1: Create Tool from URL

```
POST /tools/from-url
    │
    ├─ ValidationsService.validateAuth(auth)
    │
    ├─ Download spec from URL (axios)
    │
    ├─ ValidationsService.validateOpenApiSpec(spec)
    │
    ├─ S3Service.uploadOpenApiSpec(spec, toolName, gatewayId)
    │  └─ S3 Upload → s3Uri returned
    │
    ├─ CredentialsService.createOrGetApiKeyCredentialProvider(name, apiKey)
    │  └─ AWS Call → credentialProviderArn returned
    │
    └─ ToolsService.createGatewayTarget(gatewayId, targetName, s3Uri, arn, ...)
       └─ AWS Call → target created ✓
```

### Example 2: Create Gateway

```
POST /gateways
    │
    ├─ GatewayService.createAgentCoreGatewayRole(roleName)
    │  └─ Create IAM role → roleArn returned
    │
    └─ GatewayService.createGateway(name, roleArn, isAuth, authConfig)
       └─ AWS Call → gateway created ✓
```

## Copying Services to Other Projects

### Step 1: Copy the service file
```bash
cp ts-version/src/services/gateways/gateway.service.ts \
   my-other-project/src/services/gateways/
```

### Step 2: Add to module
```typescript
// my-other-project/src/services/services.module.ts
import { GatewayService } from './gateways/gateway.service';

@Module({
  providers: [GatewayService],
  exports: [GatewayService],
})
export class ServicesModule {}
```

### Step 3: Use in your controller/service
```typescript
import { GatewayService } from './services/gateways/gateway.service';

@Injectable()
export class MyService {
  constructor(private readonly gatewayService: GatewayService) {}

  async myMethod() {
    const gateway = await this.gatewayService.getGateway('gw-123');
    // ... use gateway
  }
}
```

**That's it!** No modifications needed.

## Why This Architecture Works

1. **Separation of Concerns**
   - Services handle AWS operations only
   - Controllers handle HTTP routing and orchestration
   - Validations are isolated

2. **Testability**
   - Each service can be tested independently
   - Mock AWS SDK for unit tests
   - No HTTP layer dependencies

3. **Reusability**
   - Copy any service to another NestJS project
   - Works in CLI apps, scheduled tasks, Lambda functions
   - No framework-specific logic in services

4. **Scalability**
   - Easy to add new services
   - Easy to change AWS SDK versions
   - Easy to add cross-cutting concerns (logging, metrics)

5. **Maintainability**
   - Clear responsibility per service
   - Changes isolated to relevant service
   - Easy to debug and extend

## Environment Variables Required

```env
AWS_DEFAULT_REGION=us-east-1              # All services
OPENAPI_SPECS_BUCKET=bucket-name         # S3Service
PORT=3000                                  # NestJS server
NODE_ENV=development                       # Optional
```

## Error Handling

All services throw meaningful errors that the controller catches:

```typescript
try {
  await credentialsService.createOrGetApiKeyCredentialProvider(name, key);
} catch (error) {
  if (error.message?.includes('already exists')) {
    // Handle duplicate
  }
  throw error; // Let controller convert to HTTP response
}
```

---

**This architecture makes the services truly portable and reusable! 🎯**

