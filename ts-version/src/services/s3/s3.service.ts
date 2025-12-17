import { Injectable, Logger } from '@nestjs/common';
import { randomBytes } from 'crypto';
import {
  S3Client,
  CreateBucketCommand,
  PutObjectCommand,
  HeadBucketCommand,
} from '@aws-sdk/client-s3';
import { STSClient, GetCallerIdentityCommand } from '@aws-sdk/client-sts';

@Injectable()
export class S3Service {
  private readonly logger = new Logger(S3Service.name);
  private readonly awsRegion = process.env.AWS_DEFAULT_REGION || 'us-east-1';

  private async ensureS3Bucket(bucketName?: string): Promise<string> {
    const s3Client = new S3Client({ region: this.awsRegion });
    const stsClient = new STSClient({ region: this.awsRegion });

    if (!bucketName) {
      const identity = await stsClient.send(new GetCallerIdentityCommand({}));
      const accountId = identity.Account;
      bucketName = `agentcore-gateways-targets-openapi-specs-${accountId}-${this.awsRegion}`;
    }

    this.logger.log(`Ensuring S3 bucket exists: ${bucketName}`);

    try {
      // Check if bucket exists
      await s3Client.send(
        new HeadBucketCommand({ Bucket: bucketName }),
      );
      this.logger.log('✓ S3 bucket already exists.');
    } catch (error: any) {
      if (error.Code === 'NoSuchBucket' || error.$metadata?.httpStatusCode === 404) {
        // Bucket doesn't exist, create it
        try {
          const createParams: any = { Bucket: bucketName };

          if (this.awsRegion !== 'us-east-1') {
            createParams.CreateBucketConfiguration = {
              LocationConstraint: this.awsRegion,
            };
          }

          await s3Client.send(new CreateBucketCommand(createParams));
          this.logger.log('✓ Created S3 bucket.');
        } catch (createError: any) {
          if (
            createError.Code === 'BucketAlreadyOwnedByYou' ||
            createError.Code === 'BucketAlreadyExists'
          ) {
            this.logger.log('✓ S3 bucket already exists.');
          } else {
            throw createError;
          }
        }
      } else {
        throw error;
      }
    }

    return bucketName;
  }

  async uploadOpenApiSpec(
    specJson: Record<string, any>,
    toolName: string,
    gatewayId: string,
    bucketName?: string,
  ): Promise<string> {
    const s3Client = new S3Client({ region: this.awsRegion });

    const finalBucketName = await this.ensureS3Bucket(bucketName);

    // Build hierarchical object key
    const timestamp = Math.floor(Date.now() / 1000);
    const randomId = randomBytes(8).toString('hex');
    const objectKey = `gateways/${gatewayId}/tools/${toolName}/${timestamp}-${randomId}.json`;
    const body = JSON.stringify(specJson);

    this.logger.log(`Uploading OpenAPI spec to S3: ${objectKey}`);

    await s3Client.send(
      new PutObjectCommand({
        Bucket: finalBucketName,
        Key: objectKey,
        Body: body,
        ContentType: 'application/json',
      }),
    );

    this.logger.log('✓ OpenAPI spec uploaded.');

    const s3Uri = `s3://${finalBucketName}/${objectKey}`;
    this.logger.log(`S3 URI: ${s3Uri}`);

    return s3Uri;
  }
}

