import { Module } from '@nestjs/common';
import { CredentialsService } from './credentials/credentials.service';
import { S3Service } from './s3/s3.service';
import { GatewayService } from './gateways/gateway.service';
import { ToolsService } from './tools/tools.service';
import { OpenApiGeneratorService } from './openapi-generator/openapi-generator.service';

@Module({
  providers: [
    CredentialsService,
    S3Service,
    GatewayService,
    ToolsService,
    OpenApiGeneratorService,
  ],
  exports: [
    CredentialsService,
    S3Service,
    GatewayService,
    ToolsService,
    OpenApiGeneratorService,
  ],
})
export class ServicesModule {}

