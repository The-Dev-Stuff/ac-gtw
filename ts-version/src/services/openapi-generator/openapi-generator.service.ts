import { Injectable, Logger } from '@nestjs/common';

@Injectable()
export class OpenApiGeneratorService {
  private readonly logger = new Logger(OpenApiGeneratorService.name);

  generateOpenApiSpec(
    toolName: string,
    method: string,
    url: string,
    queryParams?: Record<string, any>,
    headers?: Record<string, any>,
    bodySchema?: Record<string, any>,
    description?: string,
  ): Record<string, any> {
    this.logger.log(`Generating OpenAPI spec for tool: ${toolName}`);

    // Parse URL to extract path
    let path = '/';
    try {
      const urlObj = new URL(url);
      path = urlObj.pathname || '/';
    } catch (e) {
      this.logger.warn(`Could not parse URL: ${url}, using default path`);
    }

    // Build parameters array
    const parameters: any[] = [];

    // Add query parameters
    if (queryParams && typeof queryParams === 'object') {
      Object.entries(queryParams).forEach(([paramName, paramSchema]) => {
        parameters.push({
          name: paramName,
          in: 'query',
          required: true,
          schema: paramSchema || { type: 'string' },
        });
      });
    }

    // Add header parameters
    if (headers && typeof headers === 'object') {
      Object.entries(headers).forEach(([headerName, headerSchema]) => {
        parameters.push({
          name: headerName,
          in: 'header',
          required: true,
          schema: headerSchema || { type: 'string' },
        });
      });
    }

    // Build request body if schema provided
    const requestBody: any = {};
    if (bodySchema && typeof bodySchema === 'object') {
      requestBody.required = true;
      requestBody.content = {
        'application/json': {
          schema: bodySchema,
        },
      };
    }

    // Build the operation object
    const operation: any = {
      summary: description || `${method} ${path}`,
      description: description || `Call ${method} endpoint at ${url}`,
      parameters: parameters,
      responses: {
        200: {
          description: 'Successful response',
          content: {
            'application/json': {
              schema: {
                type: 'object',
              },
            },
          },
        },
        400: {
          description: 'Bad request',
        },
        401: {
          description: 'Unauthorized',
        },
        500: {
          description: 'Internal server error',
        },
      },
    };

    if (Object.keys(requestBody).length > 0) {
      operation.requestBody = requestBody;
    }

    // Build the OpenAPI spec
    const spec: Record<string, any> = {
      openapi: '3.1.0',
      info: {
        title: toolName,
        description: description || `OpenAPI spec for ${toolName}`,
        version: '1.0.0',
      },
      servers: [
        {
          url: url.split('/api')[0], // Base URL
          description: 'Default server',
        },
      ],
      paths: {
        [path]: {
          [method.toLowerCase()]: operation,
        },
      },
    };

    this.logger.log(`Generated OpenAPI spec with ${parameters.length} parameters`);

    return spec;
  }
}

