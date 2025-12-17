import { Injectable, Logger } from '@nestjs/common';
import {
  BedrockAgentCoreControlClient,
  CreateGatewayCommand,
  GetGatewayCommand,
  ListGatewaysCommand,
  UpdateGatewayCommand,
  DeleteGatewayCommand,
} from '@aws-sdk/client-bedrock-agentcore-control';

@Injectable()
export class GatewayService {
  private readonly logger = new Logger(GatewayService.name);
  private readonly awsRegion = process.env.AWS_DEFAULT_REGION || 'us-east-1';
  private readonly gatewayRoleArn = process.env.GATEWAY_ROLE_ARN;

  async getGateway(gatewayId: string): Promise<Record<string, any>> {
    const client = new BedrockAgentCoreControlClient({
      region: this.awsRegion,
    });

    this.logger.log(`Retrieving gateway: ${gatewayId}...`);

    try {
      const command = new GetGatewayCommand({
        gatewayIdentifier: gatewayId,
      });

      const response = await client.send(command);
      this.logger.log(`✓ Gateway retrieved. Name: ${response.name}`);
      return response as Record<string, any>;
    } catch (error: any) {
      if (error.name === 'ResourceNotFoundException') {
        throw new Error(`Gateway '${gatewayId}' not found`);
      }
      throw error;
    }
  }

  async listGateways(
    maxResults?: number,
    nextToken?: string,
  ): Promise<Record<string, any>> {
    const client = new BedrockAgentCoreControlClient({
      region: this.awsRegion,
    });

    this.logger.log('Listing all gateways...');

    const listParams: any = {};

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
      const command = new ListGatewaysCommand(listParams);
      const response = await client.send(command);
      const items = response.items || [];
      this.logger.log(`✓ Retrieved ${items.length} gateway(s).`);
      if (response.nextToken) {
        this.logger.log('  More results available. Use nextToken to fetch more.');
      }
      return response as Record<string, any>;
    } catch (error) {
      throw error;
    }
  }

  async createGateway(
    gatewayName: string,
    roleArn: string,
    isAuthenticated: boolean,
    authConfig?: Record<string, any>,
    description?: string,
  ): Promise<Record<string, any>> {
    const client = new BedrockAgentCoreControlClient({
      region: this.awsRegion,
    });

    this.logger.log(`Creating gateway: ${gatewayName}...`);

    try {
      let response;

      if (isAuthenticated) {
        response = await this.createGatewayWithAuth(
          client,
          gatewayName,
          roleArn,
          authConfig,
          description,
        );
        this.logger.log('✓ Gateway created with JWT auth.');
      } else {
        response = await this.createGatewayWithoutAuth(
          client,
          gatewayName,
          roleArn,
          description,
        );
        this.logger.log('✓ Gateway created without auth.');
      }

      this.logger.log('Gateway info:');
      Object.entries(response).forEach(([k, v]) => {
        this.logger.log(`  ${k}: ${v}`);
      });

      const gatewayId = response.gatewayId;
      const gatewayUrl = response.gatewayUrl;

      this.logger.log(`Gateway ID: ${gatewayId}`);
      this.logger.log(`Gateway URL: ${gatewayUrl}`);

      if (!gatewayId || !gatewayUrl) {
        throw new Error(`Invalid gateway response: ${JSON.stringify(response)}`);
      }

      return response as Record<string, any>;
    } catch (error) {
      throw error;
    }
  }

  private async createGatewayWithAuth(
    client: BedrockAgentCoreControlClient,
    gatewayName: string,
    roleArn: string,
    authConfig?: Record<string, any>,
    description?: string,
  ): Promise<Record<string, any>> {
    if (!authConfig?.client_id || !authConfig?.discovery_url) {
      throw new Error(
        'auth_config.client_id and auth_config.discovery_url are required for authenticated gateways',
      );
    }

    const command = new CreateGatewayCommand({
      name: gatewayName,
      protocolType: 'MCP',
      authorizerType: 'CUSTOM_JWT',
      roleArn: roleArn,
      description: description,
    });

    return await client.send(command);
  }

  private async createGatewayWithoutAuth(
    client: BedrockAgentCoreControlClient,
    gatewayName: string,
    roleArn: string,
    description?: string,
  ): Promise<Record<string, any>> {
    const command = new CreateGatewayCommand({
      name: gatewayName,
      protocolType: 'MCP',
      authorizerType: 'NONE',
      roleArn: roleArn,
      description: description,
    });

    return await client.send(command);
  }

  async updateGateway(
    gatewayId: string,
    name: string,
    protocolType: string,
    authorizerType: string,
    roleArn: string,
    description?: string,
    authorizerConfiguration?: Record<string, any>,
  ): Promise<Record<string, any>> {
    const client = new BedrockAgentCoreControlClient({
      region: this.awsRegion,
    });

    this.logger.log(`Updating gateway: ${gatewayId}...`);

    const updateParams: any = {
      gatewayIdentifier: gatewayId,
      name: name,
      protocolType: protocolType,
      authorizerType: authorizerType,
      roleArn: roleArn,
    };

    if (description !== undefined) {
      updateParams.description = description;
    }

    if (authorizerConfiguration !== undefined) {
      updateParams.authorizerConfiguration = authorizerConfiguration;
    }

    try {
      const command = new UpdateGatewayCommand(updateParams);
      const response = await client.send(command);
      this.logger.log('✓ Gateway updated.');

      this.logger.log(`  Gateway ID: ${response.gatewayId}`);
      this.logger.log(`  Gateway URL: ${response.gatewayUrl}`);
      this.logger.log(`  Status: ${response.status}`);
      this.logger.log(`  Name: ${response.name}`);
      if (response.updatedAt) {
        this.logger.log(`  Updated At: ${response.updatedAt}`);
      }
      if (response.statusReasons) {
        this.logger.log(`  Status Reasons: ${response.statusReasons}`);
      }

      return response as Record<string, any>;
    } catch (error: any) {
      if (error.name === 'ResourceNotFoundException') {
        throw new Error(`Gateway '${gatewayId}' not found`);
      }
      throw error;
    }
  }

  async deleteGateway(gatewayId: string): Promise<void> {
    const client = new BedrockAgentCoreControlClient({
      region: this.awsRegion,
    });

    try {
      this.logger.log(`Deleting gateway ${gatewayId}...`);
      const command = new DeleteGatewayCommand({
        gatewayIdentifier: gatewayId,
      });

      await client.send(command);
      this.logger.log('✓ Gateway deleted.');
    } catch (error) {
      this.logger.error(`delete gateway error: ${error}`);
      throw error;
    }
  }
}

