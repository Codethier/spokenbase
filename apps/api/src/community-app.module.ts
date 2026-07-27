// SPDX-License-Identifier: AGPL-3.0-only

import { Module } from '@nestjs/common';

import { CommunityCoreModule } from '../../../src/community-core.module.js';

@Module({
  imports: [CommunityCoreModule],
})
export class CommunityAppModule {}
