import { Injectable, Logger } from '@nestjs/common';
import {
  BedrockAgentCoreControlClient,
  CreateGatewayTargetCommand,
  GetGatewayTargetCommand,
  ListGatewayTargetsCommand,
  UpdateGatewayTargetCommand,
  DeleteGatewayTargetCommand,
} from '@aws-sdk/client-bedrock-agentcore-control';

@Injectable()
export class ToolsService {
  private readonly logger = new Logger(ToolsService.name);
  private readonly awsRegion = process.env.AWS_DEFAULT_REGION || 'us-east-1';

  async getGatewayTarget(
    gatewayId: string,
    targetId: string,
  ): Promise<Record<string, any>> {
    const client = new BedrockAgentCoreControlClient({
      region: this.awsRegion,
    });

    this.logger.log(
      `Retrieving gateway target: ${targetId} from gateway: ${gatewayId}...`,
    );

    try {
      const command = new GetGatewayTargetCommand({
        gatewayIdentifier: gatewayId,
        targetId: targetId,
      });

      const response = await client.send(command);
      this.logger.log(
        `✓ Gateway target retrieved. Name: ${response.name}`,
      );
      return response as Record<string, any>;
    } catch (error: any) {
      if (error.name === 'ResourceNotFoundException') {
        throw new Error(
          `Target '${targetId}' not found on gateway '${gatewayId}'`,
        );
      }
      throw error;
    }
  }

  async listGatewayTargets(
    gatewayId: string,
    maxResults?: number,
    nextToken?: string,
  ): Promise<Record<string, any>> {
    const client = new BedrockAgentCoreControlClient({
      region: this.awsRegion,
    });

    this.logger.log(
      `Listing all targets for gateway: ${gatewayId}...`,
    );

    const listParams: any = {
      gatewayIdentifier: gatewayId,
    };

    if (maxResults !== undefined) {
      if (maxResults < 1 || maxResults > 1000) {
        throw new Error('maxResults must be between 1 and 1000');
      }
      listParams.maxResults = maxResults;
    }

    if (nextToken) {
      listParams.nextToken = nextToken;
    }

    try {
      const command = new ListGatewayTargetsCommand(listParams);
      const response = await client.send(command);
      const items = response.items || [];
      this.logger.log(`✓ Retrieved ${items.length} target(s).`);
      if (response.nextToken) {
        this.logger.log(
          '  More results available. Use nextToken to fetch more.',
        );
      }
      return response as Record<string, any>;
    } catch (error) {
      throw error;
    }
  }

  async createGatewayTarget(
    gatewayId: string,
    targetName: string,
    openApiS3Uri: string,
    apiKeyCredentialProviderArn: string,
    apiKeyParamName: string = 'api_key',
    apiKeyLocation: string = 'QUERY_PARAMETER',
    description?: string,
  ): Promise<Record<string, any>> {
    const client = new BedrockAgentCoreControlClient({
      region: this.awsRegion,
    });

    this.logger.log(`Creating gateway target: ${targetName}`);

    // Build target configuration with OpenAPI schema
    const targetConfig = {
      mcp: {
        openApiSchema: {
          s3: {
            uri: openApiS3Uri,
          },
        },
      },
    };

    // Build credential provider configuration
    const credentialConfigs: any = [
      {
        credentialProviderType: 'API_KEY' as const,
        credentialProvider: {
          apiKeyCredentialProvider: {
            credentialParameterName: apiKeyParamName,
            providerArn: apiKeyCredentialProviderArn,
            credentialLocation: apiKeyLocation,
          },
        },
      },
    ];

    try {
      const command = new CreateGatewayTargetCommand({
        gatewayIdentifier: gatewayId,
        name: targetName,
        description: description || `OpenAPI target: ${targetName}`,
        targetConfiguration: targetConfig,
        credentialProviderConfigurations: credentialConfigs,
      });

      const response = await client.send(command);
      this.logger.log('✓ Gateway target created.');

      this.logger.log(`  Target ID: ${response.targetId}`);
      this.logger.log(`  Gateway ARN: ${response.gatewayArn}`);
      this.logger.log(`  Status: ${response.status}`);
      this.logger.log(`  Name: ${response.name}`);
      if (response.createdAt) {
        this.logger.log(`  Created At: ${response.createdAt}`);
      }
      if (response.statusReasons) {
        this.logger.log(
          `  Status Reasons: ${JSON.stringify(response.statusReasons)}`,
        );
      }

      return response as Record<string, any>;
    } catch (error: any) {
      if (error.Code === 'ConflictException') {
        this.logger.warn(
          `✗ Target name already exists for this gateway.`,
        );
        throw new Error(
          `Target '${targetName}' already exists on gateway ${gatewayId}`,
        );
      }
      throw error;
    }
  }

  async updateGatewayTarget(
    gatewayId: string,
    targetId: string,
    targetName: string,
    targetConfiguration?: Record<string, any>,
    description?: string,
    credentialProviderConfigurations?: Record<string, any>[],
  ): Promise<Record<string, any>> {
    const client = new BedrockAgentCoreControlClient({
      region: this.awsRegion,
    });

    this.logger.log(
      `Updating gateway target: ${targetId} on gateway: ${gatewayId}`,
    );

    // Fetch existing target to preserve S3 URI and credentials if not provided
    let existingTarget: Record<string, any> | null = null;
    try {
      existingTarget = await this.getGatewayTarget(gatewayId, targetId);
    } catch (e) {
      this.logger.warn(
        `Warning: Could not fetch existing target: ${String(e)}`,
      );
    }

    // If target_configuration not provided, use existing
    let finalTargetConfiguration = targetConfiguration;
    if (!finalTargetConfiguration) {
      if (existingTarget) {
        finalTargetConfiguration = existingTarget.targetConfiguration;
        this.logger.log(
          'No target configuration provided. Using existing configuration.',
        );
      } else {
        throw new Error(
          'target_configuration is required when updating tool if existing target cannot be retrieved',
        );
      }
    }

    // Build update parameters
    const updateParams: any = {
      gatewayIdentifier: gatewayId,
      targetId: targetId,
      name: targetName,
      targetConfiguration: finalTargetConfiguration,
    };

    // If target_configuration has an empty S3 URI, preserve existing one
    if (existingTarget && finalTargetConfiguration) {
      const existingS3Uri =
        existingTarget?.targetConfiguration?.mcp?.openApiSchema?.s3?.uri;

      const newS3Uri =
        finalTargetConfiguration?.mcp?.openApiSchema?.s3?.uri;

      if (!newS3Uri && existingS3Uri) {
        this.logger.log(
          `No S3 URI provided in update. Using existing S3 URI: ${existingS3Uri}`,
        );
        if (finalTargetConfiguration.mcp?.openApiSchema?.s3) {
          finalTargetConfiguration.mcp.openApiSchema.s3.uri = existingS3Uri;
        }
        updateParams.targetConfiguration = finalTargetConfiguration;
      }
    }

    // Add credential configurations if provided
    if (credentialProviderConfigurations !== undefined) {
      updateParams.credentialProviderConfigurations =
        credentialProviderConfigurations;
    } else if (existingTarget) {
      const existingCreds =
        existingTarget.credentialProviderConfigurations;
      if (existingCreds) {
        updateParams.credentialProviderConfigurations = existingCreds;
        this.logger.log(
          'Using existing credential configurations from current target',
        );
      }
    }

    // Add optional parameters if provided
    if (description !== undefined) {
      updateParams.description = description;
    }

    this.logger.log(`Update params: ${JSON.stringify(updateParams)}`);

    try {
      const command = new UpdateGatewayTargetCommand(updateParams);
      const response = await client.send(command);
      this.logger.log('✓ Gateway target updated.');

      this.logger.log(`  Target ID: ${response.targetId}`);
      this.logger.log(`  Gateway ARN: ${response.gatewayArn}`);
      this.logger.log(`  Status: ${response.status}`);
      this.logger.log(`  Name: ${response.name}`);
      if (response.updatedAt) {
        this.logger.log(`  Updated At: ${response.updatedAt}`);
      }
      if (response.statusReasons) {
        this.logger.log(
          `  Status Reasons: ${JSON.stringify(response.statusReasons)}`,
        );
      }

      return response as Record<string, any>;
    } catch (error: any) {
      if (error.name === 'ResourceNotFoundException') {
        throw new Error(
          `Target '${targetId}' not found on gateway '${gatewayId}'`,
        );
      }
      throw error;
    }
  }

  async deleteGatewayTarget(
    gatewayId: string,
    targetId: string,
  ): Promise<Record<string, any>> {
    const client = new BedrockAgentCoreControlClient({
      region: this.awsRegion,
    });

    this.logger.log(
      `Deleting gateway target: ${targetId} from gateway: ${gatewayId}`,
    );

    try {
      const command = new DeleteGatewayTargetCommand({
        gatewayIdentifier: gatewayId,
        targetId: targetId,
      });

      const response = await client.send(command);
      this.logger.log(
        `✓ Gateway target deletion initiated. Status: ${response.status}`,
      );
      return response as Record<string, any>;
    } catch (error: any) {
      if (error.name === 'ResourceNotFoundException') {
        throw new Error(
          `Target '${targetId}' not found on gateway '${gatewayId}'`,
        );
      }
      throw error;
    }
  }
}

