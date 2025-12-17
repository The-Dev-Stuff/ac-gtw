import { IsString, IsOptional, IsEnum, ValidateNested, IsObject } from 'class-validator';
import { Type } from 'class-transformer';

export enum AuthType {
  OAUTH = 'oauth',
  API_KEY = 'api_key',
}

export enum ApiKeyLocation {
  QUERY_PARAMETER = 'QUERY_PARAMETER',
  HEADER = 'HEADER',
}

export class AuthConfigDto {
  @IsOptional()
  @IsString()
  api_key?: string;

  @IsOptional()
  @IsString()
  api_key_param_name: string = 'api_key';

  @IsOptional()
  @IsEnum(ApiKeyLocation)
  api_key_location: ApiKeyLocation = ApiKeyLocation.QUERY_PARAMETER;
}

export class AuthDto {
  @IsEnum(AuthType)
  type!: AuthType;

  @IsOptional()
  @IsString()
  provider_name?: string;

  @ValidateNested()
  @Type(() => AuthConfigDto)
  config!: AuthConfigDto;
}

export class CognitoAuthConfigDto {
  @IsString()
  user_pool_id!: string;

  @IsString()
  client_id!: string;

  @IsString()
  discovery_url!: string;
}

export class HealthCheckResponseDto {
  status!: string;
  message!: string;
  openapi_specs_bucket?: string;
  aws_region?: string;
}

// Gateway DTOs
export class CreateGatewayRequestDto {
  @IsString()
  gateway_name!: string;

  @IsOptional()
  @IsString()
  description?: string;

  @ValidateNested()
  @Type(() => CognitoAuthConfigDto)
  auth_config!: CognitoAuthConfigDto;
}

export class CreateGatewayNoAuthRequestDto {
  @IsString()
  gateway_name!: string;

  @IsOptional()
  @IsString()
  description?: string;
}

export class CreateGatewayResponseDto {
  status!: string;
  message!: string;
  gateway_id?: string;
  gateway_url?: string;
  gateway_arn?: string;
  name?: string;
  description?: string;
  created_at?: Date;
  updated_at?: Date;
  gateway_status?: string;
  status_reasons?: string[];
  authorizer_type?: string;
  protocol_type?: string;
  role_arn?: string;
  authorizer_configuration?: Record<string, any>;
  protocol_configuration?: Record<string, any>;
  exception_level?: string;
  interceptor_configurations?: Record<string, any>[];
  policy_engine_configuration?: Record<string, any>;
  kms_key_arn?: string;
  workload_identity_details?: Record<string, any>;
}

export class UpdateGatewayRequestDto {
  @IsString()
  name!: string;

  @IsString()
  protocol_type!: string;

  @IsString()
  authorizer_type!: string;

  @IsString()
  role_arn!: string;

  @IsOptional()
  @IsString()
  description?: string;
}

export class UpdateGatewayResponseDto {
  status!: string;
  message!: string;
  gateway_id?: string;
  gateway_url?: string;
  gateway_arn?: string;
  name?: string;
  description?: string;
  created_at?: Date;
  updated_at?: Date;
  gateway_status?: string;
  status_reasons?: string[];
  authorizer_type?: string;
  protocol_type?: string;
  role_arn?: string;
  authorizer_configuration?: Record<string, any>;
  protocol_configuration?: Record<string, any>;
  exception_level?: string;
  interceptor_configurations?: Record<string, any>[];
  policy_engine_configuration?: Record<string, any>;
  kms_key_arn?: string;
  workload_identity_details?: Record<string, any>;
}

export class GetGatewayResponseDto {
  status!: string;
  message!: string;
  gateway_id?: string;
  gateway_url?: string;
  gateway_arn?: string;
  name?: string;
  description?: string;
  created_at?: Date;
  updated_at?: Date;
  gateway_status?: string;
  status_reasons?: string[];
  authorizer_type?: string;
  protocol_type?: string;
  role_arn?: string;
  authorizer_configuration?: Record<string, any>;
  protocol_configuration?: Record<string, any>;
  exception_level?: string;
  interceptor_configurations?: Record<string, any>[];
  policy_engine_configuration?: Record<string, any>;
  kms_key_arn?: string;
  workload_identity_details?: Record<string, any>;
}

export class GatewaySummaryDto {
  gateway_id?: string;
  name?: string;
  description?: string;
  gateway_status?: string;
  authorizer_type?: string;
  protocol_type?: string;
  created_at?: Date;
  updated_at?: Date;
}

export class ListGatewaysResponseDto {
  status!: string;
  message!: string;
  items!: GatewaySummaryDto[];
  next_token?: string;
}

export class DeleteGatewayResponseDto {
  gateway_id!: string;
  status!: string;
  status_reasons?: string[];
}

// Tools DTOs
export class ApiInfoDto {
  @IsString()
  method!: string;

  @IsString()
  url!: string;

  @IsOptional()
  @IsObject()
  query_params?: Record<string, any>;

  @IsOptional()
  @IsObject()
  headers?: Record<string, any>;

  @IsOptional()
  @IsObject()
  body_schema?: Record<string, any>;

  @IsOptional()
  @IsString()
  description?: string;
}

export class CreateToolFromUrlRequestDto {
  @IsString()
  gateway_id!: string;

  @IsString()
  tool_name!: string;

  @IsString()
  openapi_spec_url!: string;

  @ValidateNested()
  @Type(() => AuthDto)
  auth!: AuthDto;
}

export class CreateToolFromApiInfoRequestDto {
  @IsString()
  gateway_id!: string;

  @IsString()
  tool_name!: string;

  @ValidateNested()
  @Type(() => ApiInfoDto)
  api_info!: ApiInfoDto;

  @IsOptional()
  @ValidateNested()
  @Type(() => AuthDto)
  auth?: AuthDto;
}

export class CreateToolFromSpecRequestDto {
  @IsString()
  gateway_id!: string;

  @IsString()
  tool_name!: string;

  @IsObject()
  openapi_spec!: Record<string, any>;

  @IsOptional()
  @ValidateNested()
  @Type(() => AuthDto)
  auth?: AuthDto;
}

export class CreateToolResponseDto {
  status!: string;
  tool_name!: string;
  gateway_id!: string;
  openapi_spec_path!: string;
  message!: string;
  target_id?: string;
  gateway_arn?: string;
  description?: string;
  created_at?: Date;
  updated_at?: Date;
  last_synchronized_at?: Date;
  target_status?: string;
  status_reasons?: string[];
  target_configuration?: Record<string, any>;
  credential_provider_configurations?: Record<string, any>[];
}

export class UpdateToolRequestDto {
  @IsString()
  target_name!: string;

  @IsOptional()
  @IsObject()
  target_configuration?: Record<string, any>;

  @IsOptional()
  @IsObject()
  credential_provider_configurations?: Record<string, any>[];

  @IsOptional()
  @IsString()
  description?: string;
}

export class UpdateToolResponseDto {
  status!: string;
  tool_name!: string;
  target_id!: string;
  gateway_id!: string;
  message!: string;
  gateway_arn?: string;
  description?: string;
  created_at?: Date;
  updated_at?: Date;
  last_synchronized_at?: Date;
  target_status?: string;
  status_reasons?: string[];
  target_configuration?: Record<string, any>;
  credential_provider_configurations?: Record<string, any>[];
}

export class GetGatewayTargetResponseDto {
  status!: string;
  message!: string;
  target_id?: string;
  name?: string;
  description?: string;
  gateway_arn?: string;
  created_at?: Date;
  updated_at?: Date;
  last_synchronized_at?: Date;
  target_status?: string;
  status_reasons?: string[];
  target_configuration?: Record<string, any>;
  credential_provider_configurations?: Record<string, any>[];
}

export class TargetSummaryDto {
  target_id?: string;
  name?: string;
  description?: string;
  target_status?: string;
  created_at?: Date;
  updated_at?: Date;
}

export class ListGatewayTargetsResponseDto {
  status!: string;
  message!: string;
  items!: TargetSummaryDto[];
  next_token?: string;
}

export class DeleteToolResponseDto {
  status!: string;
  target_id!: string;
  gateway_id!: string;
  gateway_arn?: string;
  status_reasons?: string[];
  message!: string;
}

