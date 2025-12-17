import { Injectable, BadRequestException, Logger } from '@nestjs/common';
import { AuthDto } from '../dtos';

@Injectable()
export class ValidationsService {
  private readonly logger = new Logger(ValidationsService.name);

  validateAuth(auth?: AuthDto): void {
    /**
     * Validate auth object if provided.
     * If auth was not provided, this function returns early, so execution can continue.
     *
     * If auth is provided with type 'api_key', ensures required fields are present.
     */
    if (!auth || auth.type !== 'api_key') {
      return;
    }

    if (!auth.config?.api_key) {
      throw new BadRequestException(
        'api_key is required in auth.config when auth.type is "api_key"',
      );
    }

    if (!auth.provider_name) {
      throw new BadRequestException(
        'auth.provider_name is required when auth.type is "api_key"',
      );
    }

    this.logger.log('✓ Auth validation passed');
  }

  validateOpenApiSpec(spec: Record<string, any>): void {
    /**
     * Validate that the spec has required OpenAPI fields
     */
    if (!spec.openapi && !spec.swagger) {
      throw new BadRequestException(
        "OpenAPI spec must contain 'openapi' or 'swagger' field",
      );
    }

    this.logger.log('✓ OpenAPI spec validation passed');
  }
}

