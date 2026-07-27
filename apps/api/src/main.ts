// SPDX-License-Identifier: AGPL-3.0-only

import 'reflect-metadata';

import { NestFactory } from '@nestjs/core';

import { CommunityAppModule } from './community-app.module.js';

const port = Number.parseInt(process.env.PORT ?? '3001', 10);
const host = process.env.HOST ?? '0.0.0.0';

const app = await NestFactory.create(CommunityAppModule);
await app.listen(port, host);
