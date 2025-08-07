#!/usr/bin/env python3
"""
LiveKit Outbound Caller Dispatch Script
Matches the exact implementation of agent.py for seamless integration
"""

import os
import asyncio
import sys
import json
from typing import Optional
from livekit import api
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv(dotenv_path=".env.local")

class OutboundCallDispatcher:
    def __init__(self):
        # Validate environment variables (same as agent.py)
        self.livekit_url = os.getenv('LIVEKIT_URL')
        self.api_key = os.getenv('LIVEKIT_API_KEY')
        self.api_secret = os.getenv('LIVEKIT_API_SECRET')
        self.outbound_trunk_id = os.getenv('SIP_OUTBOUND_TRUNK_ID')
        
        # Validate required variables
        required_vars = {
            'LIVEKIT_URL': self.livekit_url,
            'LIVEKIT_API_KEY': self.api_key,
            'LIVEKIT_API_SECRET': self.api_secret,
            'SIP_OUTBOUND_TRUNK_ID': self.outbound_trunk_id
        }
        
        for var_name, var_value in required_vars.items():
            if not var_value:
                raise ValueError(f"❌ Missing environment variable: {var_name}")
        
        # Validate SIP trunk ID format (same validation as agent.py)
        if not self.outbound_trunk_id.startswith("ST_"):
            raise ValueError("❌ SIP_OUTBOUND_TRUNK_ID must start with 'ST_'")
        
        # Create LiveKit API client
        self.lk_api = api.LiveKitAPI(
            url=self.livekit_url,
            api_key=self.api_key,
            api_secret=self.api_secret
        )
    
    def parse_metadata(self, metadata: str) -> dict:
        """
        Parse metadata - supports both JSON and simple phone number formats
        Matches the dynamic parsing from agent.py
        """
        try:
            # Try to parse as JSON first
            if metadata.strip().startswith('{'):
                parsed = json.loads(metadata)
                return {
                    'phone_number': parsed.get('phone_number', parsed.get('phone', metadata)),
                    'first_name': parsed.get('first_name', 'there'),
                    'city': parsed.get('city', 'your area'),
                    'address': parsed.get('address', 'your property')
                }
        except (json.JSONDecodeError, AttributeError):
            pass
        
        # Fallback to simple phone number format
        return {
            'phone_number': metadata.strip(),
            'first_name': 'there',
            'city': 'your area', 
            'address': 'your property'
        }
    
    async def create_sip_participant(self, room_name: str, phone_number: str):
        """
        Create SIP participant exactly like agent.py does
        """
        user_identity = f"sip-user-{int(time.time())}"
        
        request = api.CreateSIPParticipantRequest(
            sip_trunk_id=self.outbound_trunk_id,
            sip_call_to=phone_number,
            room_name=room_name,
            participant_identity=user_identity,
            participant_name=f"Caller {phone_number}",
            participant_metadata=json.dumps({
                "phone_number": phone_number,
                "call_type": "outbound",
                "created_at": int(time.time())
            })
        )
        
        return await self.lk_api.sip.create_sip_participant(request)
    
    async def dispatch_call(self, metadata: str, room_name: Optional[str] = None) -> bool:
        """
        Dispatch outbound call with the same logic as agent.py entrypoint
        """
        try:
            # Parse metadata (JSON or simple phone number)
            call_data = self.parse_metadata(metadata)
            phone_number = call_data['phone_number']
            
            # Generate room name if not provided
            if not room_name:
                room_name = f"outbound-call-{int(time.time())}"
            
            print(f"🚀 Dispatching LiveKit Outbound Call")
            print(f"=" * 50)
            print(f"📞 Phone Number: {phone_number}")
            print(f"🏠 Room Name: {room_name}")
            print(f"🔧 SIP Trunk: {self.outbound_trunk_id}")
            print(f"👤 Caller Info: {call_data['first_name']} in {call_data['city']}")
            print(f"🏡 Property: {call_data['address']}")
            
            # Create room first
            room_request = api.CreateRoomRequest(
                name=room_name,
                metadata=metadata
            )
            
            room = await self.lk_api.room.create_room(room_request)
            print(f"✅ Room created: {room.name} (SID: {room.sid})")
            
            # Create SIP participant (this triggers the outbound call)
            print(f"📱 Initiating SIP call...")
            sip_response = await self.create_sip_participant(room_name, phone_number)
            
            print(f"✅ SIP participant created!")
            if hasattr(sip_response, 'participant'):
                print(f"🎯 Participant SID: {sip_response.participant.sid}")
                print(f"🔗 Participant Identity: {sip_response.participant.identity}")
            else:
                print(f"📋 Response: {sip_response}")
            
            # Wait a moment for the agent to connect
            print(f"⏳ Waiting for agent to connect...")
            await asyncio.sleep(2)
            
            # Check if agent connected
            participants = await self.lk_api.room.list_participants(
                api.ListParticipantsRequest(room=room_name)
            )
            
            agent_connected = any(
                p.identity == "outbound-caller" or "agent" in p.identity.lower() 
                for p in participants.participants
            )
            
            if agent_connected:
                print(f"🤖 Agent connected successfully!")
            else:
                print(f"⚠️  Agent not yet connected (may take a moment)")
            
            print(f"\n🎉 Call dispatch completed successfully!")
            print(f"📊 Total participants: {len(participants.participants)}")
            print(f"💡 Monitor your agent logs for call progress")
            
            return True
            
        except Exception as e:
            print(f"❌ Error dispatching call: {e}")
            print(f"🔍 Check your environment variables and SIP trunk configuration")
            return False
    
    async def list_active_rooms(self):
        """List all active rooms for monitoring"""
        try:
            rooms = await self.lk_api.room.list_rooms(api.ListRoomsRequest())
            
            print(f"📊 Active LiveKit Rooms: {len(rooms.rooms)}")
            print(f"=" * 40)
            
            for room in rooms.rooms:
                participants = await self.lk_api.room.list_participants(
                    api.ListParticipantsRequest(room=room.name)
                )
                
                print(f"🏠 Room: {room.name}")
                print(f"   📞 Metadata: {room.metadata}")
                print(f"   👥 Participants: {len(participants.participants)}")
                print(f"   ⏰ Created: {room.creation_time}")
                
                for p in participants.participants:
                    status = "🟢 Connected" if p.state == api.ParticipantInfo.State.ACTIVE else "🔴 Disconnected"
                    print(f"     - {p.identity} ({status})")
                print()
                
        except Exception as e:
            print(f"❌ Error listing rooms: {e}")

async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("📱 LiveKit Outbound Call Dispatcher")
        print("=" * 40)
        print("Usage:")
        print("  python3 dispatch_call.py <phone_number>")
        print("  python3 dispatch_call.py <json_metadata>")
        print("  python3 dispatch_call.py --list-rooms")
        print()
        print("Examples:")
        print('  python3 dispatch_call.py "+923024491162"')
        print('  python3 dispatch_call.py \'{"phone_number": "+923024491162", "first_name": "John", "city": "Karachi"}\'')
        print("  python3 dispatch_call.py --list-rooms")
        sys.exit(1)
    
    try:
        dispatcher = OutboundCallDispatcher()
        
        if sys.argv[1] == "--list-rooms":
            await dispatcher.list_active_rooms()
        else:
            metadata = sys.argv[1]
            success = await dispatcher.dispatch_call(metadata)
            sys.exit(0 if success else 1)
            
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
