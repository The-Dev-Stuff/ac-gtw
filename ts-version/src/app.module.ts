import { Module } from '@nestjs/common';
import { AppController } from './api/app.controller';
import { ServicesModule } from './services/services.module';
import { ValidationsService } from './api/validations/validations.service';

@Module({
  imports: [ServicesModule],
  controllers: [AppController],
  providers: [ValidationsService],
})
export class AppModule {}

