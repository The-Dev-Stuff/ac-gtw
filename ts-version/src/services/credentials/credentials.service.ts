import { Injectable, Logger } from '@nestjs/common';
import {
  BedrockAgentCoreControlClient,
  CreateApiKeyCredentialProviderCommand,
} from '@aws-sdk/client-bedrock-agentcore-control';

@Injectable()
export class CredentialsService {
  private readonly logger = new Logger(CredentialsService.name);
  private readonly awsRegion = process.env.AWS_DEFAULT_REGION || 'us-east-1';

  async createOrGetApiKeyCredentialProvider(
    providerName: string,
    apiKey: string,
  ): Promise<string> {
    const client = new BedrockAgentCoreControlClient({
      region: this.awsRegion,
    });

    this.logger.log(
      `Creating/retrieving credential provider: ${providerName}`,
    );

    try {
      const command = new CreateApiKeyCredentialProviderCommand({
        name: providerName,
        apiKey: apiKey,
      });

      const response = await client.send(command);
      const credentialProviderArn = response.credentialProviderArn || '';
      this.logger.log('✓ Credential provider created.');

      this.logger.log(`Credential provider ARN: ${credentialProviderArn}`);
      return credentialProviderArn;
    } catch (error: any) {
      if (
        error.message?.includes('already exists') ||
        error.Code === 'EntityAlreadyExists'
      ) {
        this.logger.log('✓ Credential provider already exists.');
        throw new Error(
          `Credential provider '${providerName}' already exists. ` +
            'Please use a unique name or handle provider updates manually.',
        );
      }
      throw error;
    }
  }
}

