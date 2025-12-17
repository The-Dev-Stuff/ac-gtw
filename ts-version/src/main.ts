import 'dotenv/config';
import 'reflect-metadata';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { ValidationPipe } from '@nestjs/common';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Enable validation pipe
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: false,
      transform: true,
    }),
  );

  const port = process.env.PORT || 3000;

  console.log('Starting AgentCore Gateway Tools API...');
  console.log(`OpenAPI specs bucket: ${process.env.OPENAPI_SPECS_BUCKET || 'agentcore-gateway-openapi-specs-bucket'}`);
  console.log(`AWS Region: ${process.env.AWS_DEFAULT_REGION || 'us-east-1'}`);

  await app.listen(port);
  console.log(`Server running on http://localhost:${port}`);
}

bootstrap();

