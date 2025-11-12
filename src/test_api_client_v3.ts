/**
 * Test script for V3 API client
 * Run with: npx tsx src/test_api_client_v3.ts
 */

import { apiClient } from './lib/api';

async function runTests() {
  console.log('🔬 Testing V3 API Client\n');
  console.log('=' .repeat(80));

  try {
    // Test 1: List sessions
    console.log('\n📋 Test 1: List Sessions (V3)');
    const sessions = await apiClient.getSessionsV3({ limit: 10 });
    console.log(`✅ Found ${sessions.total} sessions`);
    if (sessions.sessions.length > 0) {
      const firstSession = sessions.sessions[0];
      console.log(`   First session: ${firstSession.id}`);
      console.log(`   Total turns: ${firstSession.total_turns}`);
      console.log(`   Total interactions: ${firstSession.total_interactions}`);

      const sessionId = firstSession.id;

      // Test 2: Get session detail
      console.log(`\n📄 Test 2: Get Session Detail (V3)`);
      const sessionDetail = await apiClient.getSessionV3(sessionId);
      console.log(`✅ Session retrieved`);
      console.log(`   ID: ${sessionDetail.id}`);
      console.log(`   Title: ${sessionDetail.title}`);
      if (sessionDetail.stats) {
        console.log(`   Stats:`);
        console.log(`     - Total interactions: ${sessionDetail.stats.total_interactions}`);
        console.log(`     - Request count: ${sessionDetail.stats.request_count}`);
        console.log(`     - Response count: ${sessionDetail.stats.response_count}`);
      }

      // Test 3: Get session interactions
      console.log(`\n🔄 Test 3: Get Session Interactions`);
      const interactions = await apiClient.getSessionInteractions(sessionId, { limit: 10 });
      console.log(`✅ Retrieved ${interactions.interactions.length} of ${interactions.total} interactions`);

      // Group by turn
      const turnGroups = new Map<number, typeof interactions.interactions>();
      interactions.interactions.forEach(i => {
        if (!turnGroups.has(i.turn_number)) {
          turnGroups.set(i.turn_number, []);
        }
        turnGroups.get(i.turn_number)!.push(i);
      });

      console.log(`   Turns found: ${turnGroups.size}`);
      turnGroups.forEach((interactions, turn) => {
        const requests = interactions.filter(i => i.type === 'request').length;
        const responses = interactions.filter(i => i.type === 'response').length;
        console.log(`   Turn ${turn}: ${requests} request(s), ${responses} response(s)`);
      });

      // Test 4: Get specific turn
      if (turnGroups.size > 0) {
        const firstTurn = Array.from(turnGroups.keys())[0];
        console.log(`\n🎯 Test 4: Get Turn ${firstTurn} Interactions`);
        const turnData = await apiClient.getTurnInteractions(sessionId, firstTurn);
        console.log(`✅ Retrieved ${turnData.interactions.length} interactions for turn ${firstTurn}`);
        turnData.interactions.forEach((i, idx) => {
          console.log(`   ${idx + 1}. [${i.type}] seq=${i.sequence}`);
        });
      }

      // Test 5: Get interaction detail
      if (interactions.interactions.length > 0) {
        const firstInteraction = interactions.interactions[0];
        console.log(`\n🔍 Test 5: Get Interaction Detail`);
        const detail = await apiClient.getInteractionDetail(firstInteraction.id);
        console.log(`✅ Retrieved interaction ${detail.id}`);
        console.log(`   Type: ${detail.type}`);
        console.log(`   Turn: ${detail.turn_number}, Sequence: ${detail.sequence}`);

        if (detail.type === 'request' && 'components' in detail) {
          console.log(`   Components: ${detail.components?.length || 0}`);
        } else if (detail.type === 'response' && 'spans' in detail) {
          console.log(`   Spans: ${detail.spans?.length || 0}`);
        }
      }

      // Test 6: Get session stats
      console.log(`\n📊 Test 6: Get Session Stats`);
      const stats = await apiClient.getSessionStats(sessionId);
      console.log(`✅ Retrieved statistics`);
      console.log(`   Overall:`);
      console.log(`     - Total turns: ${stats.overall.total_turns}`);
      console.log(`     - Total interactions: ${stats.overall.total_interactions}`);
      console.log(`     - Input tokens: ${stats.overall.total_input_tokens}`);
      console.log(`     - Output tokens: ${stats.overall.total_output_tokens}`);
      console.log(`   Per-turn stats: ${stats.per_turn.length} turns`);

      // Show first 3 turns stats
      stats.per_turn.slice(0, 3).forEach(t => {
        console.log(`     Turn ${t.turn_number}: ${t.interaction_count} interactions (${t.request_count} req, ${t.response_count} resp)`);
      });
    } else {
      console.log('⚠️  No sessions found in database');
    }

    console.log('\n' + '='.repeat(80));
    console.log('✅ All V3 API tests passed!\n');

  } catch (error) {
    console.error('\n❌ Test failed:', error);
    process.exit(1);
  }
}

// Run tests
runTests();
