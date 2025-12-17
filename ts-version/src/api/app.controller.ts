import {
  Controller,
  Get,
  Post,
  Put,
  Delete,
  Param,
  Body,
  Query,
  HttpException,
  HttpStatus,
  BadRequestException,
} from '@nestjs/common';
import { GatewayService } from '../services/gateways/gateway.service';
import { ToolsService } from '../services/tools/tools.service';
import { CredentialsService } from '../services/credentials/credentials.service';
import { S3Service } from '../services/s3/s3.service';
import { OpenApiGeneratorService } from '../services/openapi-generator/openapi-generator.service';
import { ValidationsService } from './validations/validations.service';
import {
  CreateGatewayRequestDto,
  CreateGatewayNoAuthRequestDto,
  UpdateGatewayRequestDto,
  CreateToolFromUrlRequestDto,
  CreateToolFromApiInfoRequestDto,
  CreateToolFromSpecRequestDto,
  UpdateToolRequestDto,
} from './dtos';

const OPENAPI_SPECS_BUCKET =
  process.env.OPENAPI_SPECS_BUCKET || 'agentcore-gateway-openapi-specs-bucket';
const AWS_REGION = process.env.AWS_DEFAULT_REGION || 'us-east-1';
const GATEWAY_ROLE_ARN = process.env.GATEWAY_ROLE_ARN;

@Controller()
export class AppController {
  constructor(
    private readonly gatewayService: GatewayService,
    private readonly toolsService: ToolsService,
    private readonly credentialsService: CredentialsService,
    private readonly s3Service: S3Service,
    private readonly openApiGeneratorService: OpenApiGeneratorService,
    private readonly validationsService: ValidationsService,
  ) {}

  // Health check
  @Get('/health')
  health() {
    return {
      status: 'healthy',
      message: 'AgentCore Gateway Tools API is running',
      openapi_specs_bucket: OPENAPI_SPECS_BUCKET,
      aws_region: AWS_REGION,
    };
  }

  // Gateways endpoints
  @Get('/gateways')
  async listGateways(
    @Query('max_results') maxResults?: number,
    @Query('next_token') nextToken?: string,
  ) {
    try {
      if (maxResults !== undefined) {
        if (maxResults < 1 || maxResults > 1000) {
          throw new BadRequestException(
            'maxResults must be between 1 and 1000',
          );
        }
      }

      const response = await this.gatewayService.listGateways(
        maxResults,
        nextToken,
      );

      const items = (response.items || []).map((item: any) => ({
        gateway_id: item.gatewayId,
        name: item.name,
        description: item.description,
        gateway_status: item.status,
        authorizer_type: item.authorizerType,
        protocol_type: item.protocolType,
        created_at: item.createdAt,
        updated_at: item.updatedAt,
      }));

      return {
        status: 'success',
        message: `Retrieved ${items.length} gateway(s)`,
        items,
        next_token: response.nextToken,
      };
    } catch (error: any) {
      throw new HttpException(
        {
          status: HttpStatus.INTERNAL_SERVER_ERROR,
          error: error.message,
        },
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Get('/gateways/:gateway_id')
  async getGateway(@Param('gateway_id') gatewayId: string) {
    try {
      const response = await this.gatewayService.getGateway(gatewayId);

      return {
        status: 'success',
        message: `Gateway '${response.name}' retrieved successfully`,
        gateway_id: response.gatewayId,
        gateway_url: response.gatewayUrl,
        gateway_arn: response.gatewayArn,
        name: response.name,
        description: response.description,
        created_at: response.createdAt,
        updated_at: response.updatedAt,
        gateway_status: response.status,
        status_reasons: response.statusReasons,
        authorizer_type: response.authorizerType,
        protocol_type: response.protocolType,
        role_arn: response.roleArn,
        authorizer_configuration: response.authorizerConfiguration,
        protocol_configuration: response.protocolConfiguration,
        exception_level: response.exceptionLevel,
        interceptor_configurations: response.interceptorConfigurations,
        policy_engine_configuration: response.policyEngineConfiguration,
        kms_key_arn: response.kmsKeyArn,
        workload_identity_details: response.workloadIdentityDetails,
      };
    } catch (error: any) {
      if (error.message?.includes('not found')) {
        throw new HttpException(error.message, HttpStatus.NOT_FOUND);
      }
      throw new HttpException(
        {
          status: HttpStatus.INTERNAL_SERVER_ERROR,
          error: error.message,
        },
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Post('/gateways')
  async createGateway(@Body() request: CreateGatewayRequestDto) {
    try {
      if (!GATEWAY_ROLE_ARN) {
        throw new BadRequestException(
          'GATEWAY_ROLE_ARN environment variable is not configured',
        );
      }

      // Validate auth_config has required fields
      if (!request.auth_config?.user_pool_id || !request.auth_config?.client_id || !request.auth_config?.discovery_url) {
        throw new BadRequestException(
          'Missing required auth_config fields: user_pool_id, client_id, discovery_url',
        );
      }

      const authConfig = {
        client_id: request.auth_config.client_id,
        discovery_url: request.auth_config.discovery_url,
      };

      const gatewayInfo = await this.gatewayService.createGateway(
        request.gateway_name,
        GATEWAY_ROLE_ARN,
        true,
        authConfig,
        request.description,
      );

      return {
        status: 'success',
        message: `Gateway '${request.gateway_name}' successfully created`,
        gateway_id: gatewayInfo.gatewayId,
        gateway_url: gatewayInfo.gatewayUrl,
        gateway_arn: gatewayInfo.gatewayArn,
        name: gatewayInfo.name,
        description: gatewayInfo.description,
        created_at: gatewayInfo.createdAt,
        updated_at: gatewayInfo.updatedAt,
        gateway_status: gatewayInfo.status,
        status_reasons: gatewayInfo.statusReasons,
        authorizer_type: gatewayInfo.authorizerType,
        protocol_type: gatewayInfo.protocolType,
        role_arn: gatewayInfo.roleArn,
        authorizer_configuration: gatewayInfo.authorizerConfiguration,
        protocol_configuration: gatewayInfo.protocolConfiguration,
        exception_level: gatewayInfo.exceptionLevel,
        interceptor_configurations: gatewayInfo.interceptorConfigurations,
        policy_engine_configuration: gatewayInfo.policyEngineConfiguration,
        kms_key_arn: gatewayInfo.kmsKeyArn,
        workload_identity_details: gatewayInfo.workloadIdentityDetails,
      };
    } catch (error: any) {
      throw new HttpException(
        {
          status: HttpStatus.INTERNAL_SERVER_ERROR,
          error: error.message,
        },
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Post('/gateways/no-auth')
  async createGatewayNoAuth(@Body() request: CreateGatewayNoAuthRequestDto) {
    try {
      if (!GATEWAY_ROLE_ARN) {
        throw new BadRequestException(
          'GATEWAY_ROLE_ARN environment variable is not configured',
        );
      }

      const gatewayInfo = await this.gatewayService.createGateway(
        request.gateway_name,
        GATEWAY_ROLE_ARN,
        false,
        undefined,
        request.description,
      );

      return {
        status: 'success',
        message: `Gateway '${request.gateway_name}' successfully created without authentication`,
        gateway_id: gatewayInfo.gatewayId,
        gateway_url: gatewayInfo.gatewayUrl,
        gateway_arn: gatewayInfo.gatewayArn,
        name: gatewayInfo.name,
        description: gatewayInfo.description,
        created_at: gatewayInfo.createdAt,
        updated_at: gatewayInfo.updatedAt,
        gateway_status: gatewayInfo.status,
        status_reasons: gatewayInfo.statusReasons,
        authorizer_type: gatewayInfo.authorizerType,
        protocol_type: gatewayInfo.protocolType,
        role_arn: gatewayInfo.roleArn,
        authorizer_configuration: gatewayInfo.authorizerConfiguration,
        protocol_configuration: gatewayInfo.protocolConfiguration,
        exception_level: gatewayInfo.exceptionLevel,
        interceptor_configurations: gatewayInfo.interceptorConfigurations,
        policy_engine_configuration: gatewayInfo.policyEngineConfiguration,
        kms_key_arn: gatewayInfo.kmsKeyArn,
        workload_identity_details: gatewayInfo.workloadIdentityDetails,
      };
    } catch (error: any) {
      throw new HttpException(
        {
          status: HttpStatus.INTERNAL_SERVER_ERROR,
          error: error.message,
        },
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Put('/gateways/:gateway_id')
  async updateGateway(
    @Param('gateway_id') gatewayId: string,
    @Body() request: UpdateGatewayRequestDto,
  ) {
    try {
      if (!['CUSTOM_JWT', 'AWS_IAM', 'NONE'].includes(
        request.authorizer_type,
      )) {
        throw new BadRequestException(
          'authorizer_type must be one of: CUSTOM_JWT, AWS_IAM, NONE',
        );
      }

      if (request.protocol_type !== 'MCP') {
        throw new BadRequestException('protocol_type must be MCP');
      }

      const response = await this.gatewayService.updateGateway(
        gatewayId,
        request.name,
        request.protocol_type,
        request.authorizer_type,
        request.role_arn,
        request.description,
      );

      return {
        status: 'success',
        message: `Gateway '${request.name}' successfully updated`,
        gateway_id: response.gatewayId,
        gateway_url: response.gatewayUrl,
        gateway_arn: response.gatewayArn,
        name: response.name,
        description: response.description,
        created_at: response.createdAt,
        updated_at: response.updatedAt,
        gateway_status: response.status,
        status_reasons: response.statusReasons,
        authorizer_type: response.authorizerType,
        protocol_type: response.protocolType,
        role_arn: response.roleArn,
        authorizer_configuration: response.authorizerConfiguration,
        protocol_configuration: response.protocolConfiguration,
        exception_level: response.exceptionLevel,
        interceptor_configurations: response.interceptorConfigurations,
        policy_engine_configuration: response.policyEngineConfiguration,
        kms_key_arn: response.kmsKeyArn,
        workload_identity_details: response.workloadIdentityDetails,
      };
    } catch (error: any) {
      if (error instanceof BadRequestException) {
        throw error;
      }
      if (error.message?.includes('not found')) {
        throw new HttpException(error.message, HttpStatus.NOT_FOUND);
      }
      throw new HttpException(
        {
          status: HttpStatus.INTERNAL_SERVER_ERROR,
          error: error.message,
        },
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Delete('/gateways/:gateway_id')
  async deleteGateway(@Param('gateway_id') gatewayId: string) {
    try {
      await this.gatewayService.deleteGateway(gatewayId);

      return {
        gateway_id: gatewayId,
        status: 'DELETING',
      };
    } catch (error: any) {
      throw new HttpException(
        {
          status: HttpStatus.INTERNAL_SERVER_ERROR,
          error: error.message,
        },
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  // Tools endpoints
  @Get('/gateways/:gateway_id/tools')
  async listTools(
    @Param('gateway_id') gatewayId: string,
    @Query('max_results') maxResults?: number,
    @Query('next_token') nextToken?: string,
  ) {
    try {
      if (maxResults !== undefined) {
        if (maxResults < 1 || maxResults > 1000) {
          throw new BadRequestException(
            'maxResults must be between 1 and 1000',
          );
        }
      }

      const response = await this.toolsService.listGatewayTargets(
        gatewayId,
        maxResults,
        nextToken,
      );

      const items = (response.items || []).map((item: any) => ({
        target_id: item.targetId,
        name: item.name,
        description: item.description,
        target_status: item.status,
        created_at: item.createdAt,
        updated_at: item.updatedAt,
      }));

      return {
        status: 'success',
        message: `Retrieved ${items.length} target(s)`,
        items,
        next_token: response.nextToken,
      };
    } catch (error: any) {
      throw new HttpException(
        {
          status: HttpStatus.INTERNAL_SERVER_ERROR,
          error: error.message,
        },
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Get('/gateways/:gateway_id/tools/:target_id')
  async getTool(
    @Param('gateway_id') gatewayId: string,
    @Param('target_id') targetId: string,
  ) {
    try {
      const response = await this.toolsService.getGatewayTarget(
        gatewayId,
        targetId,
      );

      return {
        status: 'success',
        message: `Gateway target '${response.name}' retrieved successfully`,
        target_id: response.targetId,
        name: response.name,
        description: response.description,
        gateway_arn: response.gatewayArn,
        created_at: response.createdAt,
        updated_at: response.updatedAt,
        last_synchronized_at: response.lastSynchronizedAt,
        target_status: response.status,
        status_reasons: response.statusReasons,
        target_configuration: response.targetConfiguration,
        credential_provider_configurations:
          response.credentialProviderConfigurations,
      };
    } catch (error: any) {
      if (error.message?.includes('not found')) {
        throw new HttpException(error.message, HttpStatus.NOT_FOUND);
      }
      throw new HttpException(
        {
          status: HttpStatus.INTERNAL_SERVER_ERROR,
          error: error.message,
        },
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Post('/tools/from-url')
  async createToolFromUrl(@Body() request: CreateToolFromUrlRequestDto) {
    try {
      this.validationsService.validateAuth(request.auth);

      const response = await this.downloadAndCreateTool(
        request.gateway_id,
        request.tool_name,
        request.openapi_spec_url,
        request.auth,
      );

      return response;
    } catch (error: any) {
      throw new HttpException(
        {
          status: HttpStatus.INTERNAL_SERVER_ERROR,
          error: error.message,
        },
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Post('/tools/from-api-info')
  async createToolFromApiInfo(@Body() request: CreateToolFromApiInfoRequestDto) {
    try {
      this.validationsService.validateAuth(request.auth);

      const spec = this.openApiGeneratorService.generateOpenApiSpec(
        request.tool_name,
        request.api_info.method,
        request.api_info.url,
        request.api_info.query_params,
        request.api_info.headers,
        request.api_info.body_schema,
        request.api_info.description,
      );

      const response = await this.createToolWithSpec(
        request.gateway_id,
        request.tool_name,
        spec,
        request.auth,
        request.api_info.description,
      );

      return response;
    } catch (error: any) {
      throw new HttpException(
        {
          status: HttpStatus.INTERNAL_SERVER_ERROR,
          error: error.message,
        },
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Post('/tools/from-spec')
  async createToolFromSpec(@Body() request: CreateToolFromSpecRequestDto) {
    try {
      this.validationsService.validateAuth(request.auth);
      this.validationsService.validateOpenApiSpec(request.openapi_spec);

      const response = await this.createToolWithSpec(
        request.gateway_id,
        request.tool_name,
        request.openapi_spec,
        request.auth,
      );

      return response;
    } catch (error: any) {
      if (error instanceof BadRequestException) {
        throw error;
      }
      throw new HttpException(
        {
          status: HttpStatus.INTERNAL_SERVER_ERROR,
          error: error.message,
        },
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Put('/gateways/:gateway_id/tools/:target_id')
  async updateTool(
    @Param('gateway_id') gatewayId: string,
    @Param('target_id') targetId: string,
    @Body() request: UpdateToolRequestDto,
  ) {
    try {
      const response = await this.toolsService.updateGatewayTarget(
        gatewayId,
        targetId,
        request.target_name,
        request.target_configuration,
        request.description,
        request.credential_provider_configurations,
      );

      return {
        status: 'success',
        tool_name: request.target_name,
        target_id: response.targetId || targetId,
        gateway_id: gatewayId,
        message: `Tool '${request.target_name}' (target ${targetId}) successfully updated on gateway '${gatewayId}'`,
        gateway_arn: response.gatewayArn,
        description: response.description,
        created_at: response.createdAt,
        updated_at: response.updatedAt,
        last_synchronized_at: response.lastSynchronizedAt,
        target_status: response.status,
        status_reasons: response.statusReasons,
        target_configuration: response.targetConfiguration,
        credential_provider_configurations:
          response.credentialProviderConfigurations,
      };
    } catch (error: any) {
      if (error.message?.includes('not found')) {
        throw new HttpException(error.message, HttpStatus.NOT_FOUND);
      }
      throw new HttpException(
        {
          status: HttpStatus.INTERNAL_SERVER_ERROR,
          error: error.message,
        },
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Delete('/gateways/:gateway_id/tools/:target_id')
  async deleteTool(
    @Param('gateway_id') gatewayId: string,
    @Param('target_id') targetId: string,
  ) {
    try {
      const response = await this.toolsService.deleteGatewayTarget(
        gatewayId,
        targetId,
      );

      return {
        status: response.status || 'DELETING',
        target_id: response.targetId || targetId,
        gateway_id: gatewayId,
        gateway_arn: response.gatewayArn,
        status_reasons: response.statusReasons,
        message: `Tool '${targetId}' deletion initiated on gateway '${gatewayId}'`,
      };
    } catch (error: any) {
      if (error.message?.includes('not found')) {
        throw new HttpException(error.message, HttpStatus.NOT_FOUND);
      }
      throw new HttpException(
        {
          status: HttpStatus.INTERNAL_SERVER_ERROR,
          error: error.message,
        },
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  // Helper methods
  private async downloadAndCreateTool(
    gatewayId: string,
    toolName: string,
    specUrl: string,
    auth: any,
  ) {
    const axios = require('axios');

    const response = await axios.get(specUrl);
    const spec = response.data;

    this.validationsService.validateOpenApiSpec(spec);

    return this.createToolWithSpec(gatewayId, toolName, spec, auth);
  }

  private async createToolWithSpec(
    gatewayId: string,
    toolName: string,
    spec: Record<string, any>,
    auth: any,
    description?: string,
  ) {
    // Upload spec to S3
    const s3Uri = await this.s3Service.uploadOpenApiSpec(
      spec,
      toolName,
      gatewayId,
      OPENAPI_SPECS_BUCKET,
    );

    // Register tool with gateway
    const result = await this.registerToolWithGateway(
      gatewayId,
      toolName,
      s3Uri,
      auth,
      description,
    );

    return {
      status: 'success',
      tool_name: toolName,
      gateway_id: gatewayId,
      openapi_spec_path: s3Uri,
      message: `Tool '${toolName}' successfully created and registered on gateway ${gatewayId}`,
      target_id: result.targetId,
      gateway_arn: result.gatewayArn,
      description: result.description,
      created_at: result.createdAt,
      updated_at: result.updatedAt,
      last_synchronized_at: result.lastSynchronizedAt,
      target_status: result.status,
      status_reasons: result.statusReasons,
      target_configuration: result.targetConfiguration,
      credential_provider_configurations:
        result.credentialProviderConfigurations,
    };
  }

  private async registerToolWithGateway(
    gatewayId: string,
    targetName: string,
    openApiS3Uri: string,
    auth: any,
    description?: string,
  ) {
    let apiKey = 'placeholder-not-used';
    let apiKeyProviderName = `${targetName}-placeholder-apikey`;
    let apiKeyParamName = 'X-Placeholder-Auth';
    let apiKeyLocation = 'HEADER';

    if (auth && auth.type === 'api_key') {
      apiKey = auth.config.api_key;
      apiKeyProviderName = auth.provider_name;
      apiKeyParamName = auth.config.api_key_param_name || 'api_key';
      apiKeyLocation = auth.config.api_key_location || 'QUERY_PARAMETER';
    }

    const credentialProviderArn =
      await this.credentialsService.createOrGetApiKeyCredentialProvider(
        apiKeyProviderName,
        apiKey,
      );

    const response = await this.toolsService.createGatewayTarget(
      gatewayId,
      targetName,
      openApiS3Uri,
      credentialProviderArn,
      apiKeyParamName,
      apiKeyLocation,
      description,
    );

    return response;
  }
}

