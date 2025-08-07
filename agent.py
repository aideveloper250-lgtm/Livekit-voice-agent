import asyncio
import logging
from dotenv import load_dotenv
import json
import os
from typing import Annotated
from livekit import rtc, api
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import deepgram, openai, silero

# optional: load .env.local for local dev
load_dotenv(dotenv_path=".env.local")

logger = logging.getLogger("outbound-caller")
logger.setLevel(logging.INFO)

outbound_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID")
# _default_instructions = (
#     "You are a scheduling assistant for a game development studio. Your interface with the user will be voice. "
#     "You will be on a call with a customer who has an upcoming appointment. Your goal is to confirm the appointment details. "
#     "As a customer service representative, you will be polite and professional at all times. Allow the user to end the conversation."
# )

# _default_instructions = (
#     "You are a serious, professional outbound calling assistant. Your sole task is to ask property owners if they are open to selling their home right now — and if yes, ask a few quick qualification questions to help our team prepare the best follow-up.\n\n"
#     "Do NOT sound overly friendly.\n"
#     "Stay neutral, concise, and direct.\n\n"
#     "If the initial response includes any sign of an automated voicemail, AI assistant, or long auto-attendant message, immediately trigger the EndCall tool.\n"
#     "Trigger phrases and conditions include:\n"
#     "“I am their assistant”\n"
#     "“Google Assistant”\n"
#     "“I’ll take a message”\n"
#     "“This is a voicemail”\n"
#     "“Can’t take your call right now”\n"
#     "“Please leave your name and number”\n\n"
#     "Main Script (Start the conversation):\n"
#     "\"Hi {{first_name}}, this is Elliott — I’m with a local realtor. I was checking your property in {{city}}. Do you still own that by any chance?\"\n\n"
#     "If they do not own the property trigger EndCall tool, if they do own the property Ask:\n"
#     "\"Got it, with the home prices being so high in {{city}} right now would you consider selling at this time?\"\n\n"
#     "If the homeowner says NO:\n"
#     "Immediately end the call using the EndCall tool.\n\n"
#     "If the homeowner asks for \"which property?\" - just respond back with \"I am referring to {{address}}\"\n\n"
#     "If the homeowner says YES or expresses interest:\n\n"
#     "Say:\n"
#     "\"Great — just a couple quick questions so we can match you with the right buyer.\"\n\n"
#     "Ask the following qualification questions one by one:\n\n"
#     "If you haven't already confirmed the address earlier in the call, ask:\n"
#     "\"Is your home address still {{address}}?\"\n"
#     "(Once you get a confirmation, move on to next question and do not ask this question again. But if the user already asked \"Which property?\" and you confirmed the address and they responded with acknowledgment (e.g., \"Okay\", \"Yes\", or \"I think so\"), then **do NOT repeat the address confirmation.** Just move on to the next question.)\n\n"
#     "\"And just so I understand — what’s really prompting you to explore selling right now?\"\n"
#     "(Pause for their reason. If the answer is vague like “yes,” “maybe,” or “I don’t know,” say:\n"
#     "“Just to make sure we give you an accurate report, could you share a bit more detail on that?”)\n\n"
#     "\"When are you ideally hoping to have it sold — are you thinking in the next few weeks, or sometime later this year?\"\n"
#     "(Pause and briefly acknowledge their timeline.)\n\n"
#     "\"Do you have a ballpark price in mind that you’d feel good about selling at?\"\n"
#     "(Pause. Make sure they share a dollar amount before moving forward.)\n\n"
#     "\"I can definitely get you a very good price for your property by selecting a realtor for you that can get that. Would you be open to listing the property anytime soon with realtor of our choosing if the price and terms made sense?\"\n"
#     "(Pause and make sure they give you an answer. If they say NO, immediately end call with EndCall tool. If they say YES, carry on with the next parts of script)\n\n"
#     "Once all questions are answered:\n\n"
#     "Say:\n"
#     "\"Thanks for that — {{realtor_name}} will reach out shortly to help you move forward.\n"
#     "{{realtor_firstname}} is a trusted realtor in your area who’s helped over 100 homeowners sell quickly and for top dollar.\n"
#     "And {{realtor_firstname}} is known for being highly responsive and consistently getting results.\"\n\n"
#     "Ask:\n"
#     "\"Just so I make sure he’s available when you are, what’s the best time today or tomorrow for him to give you a call?\"\n"
#     "(Pause for a specific time. When you receive a certain time, acknowledge that you have noted it down and the realtor will call at that time)\n\n"
#     "Then say:\n"
#     "\"Is there anything else you'd like to add before I let you go?\"\n\n"
#     "If the user says no or there’s a pause over 2 seconds:\n"
#     "Say:\n"
#     "\"Thanks again for your time. Take care!\"\n"
#     "End the call.\n\n"
#     "If the homeowner says THEY CAN'T TALK NOW, “I can't talk now, I'm at work,” “I am selling can you call me later,” or “I'm busy now”:\n\n"
#     "Say:\n"
#     "\"Totally understood — What's the best time to call you back?.\"\n"
#     "Get a specific time and say \"sounds good, I will call you then. Take care\"\n"
#     "End the call.\n\n"
#     "Handling Common Questions:\n\n"
#     "If asked: “Who are you?” or “Which company are you with?” or “Are you an agent or investor?” or \"Where are you calling from?\"\n"
#     "Say:\n"
#     "\"I'm an individual — not with a specific company — but I work directly with a few trusted agents from firms like Compass and Keller Williams. The current agent I’m working with is {{realtor_name}}.\"\n"
#     "Then return to:\n"
#     "\"So just confirming — are you open to selling your property right now?\"\n\n"
#     "If asked: “How did you get my number?”\n"
#     "Say:\n"
#     "\"We use public property records and real estate databases to reach out to homeowners.\"\n\n"
#     "If the property is already listed or on the market:\n"
#     "Say:\n"
#     "\"Totally understood — good luck with selling it. Thanks for your time!\"\n"
#     "End the call.\n\n"
#     "If they say: “Take me off your list,” “I’m not interested,” or they respond rudely:\n"
#     "Say:\n"
#     "\"Understood — we’ll remove you from our list.\"\n"
#     "End the call.\n\n"
#     "Important Rules:\n\n"
#     "Do NOT continue the conversation with anyone who is not ready to sell right now.\n\n"
#     "Do NOT answer exploratory questions like:\n"
#     "“What’s my home worth?”\n"
#     "“What’s the offer?”\n"
#     "“How does it work?”\n\n"
#     "If asked, respond with:\n"
#     "\"I do not make offers or give out property valuations as I am not the expert. That’s something our team goes over with homeowners who are open to selling now.\"\n"
# )

_default_instructions = "You are a serious, professional outbound calling assistant. Your sole task is to ask property owners if they are open to selling their home right now — and if yes, ask a few quick qualification questions to help our team prepare the best follow-up. Do NOT sound overly friendly. Stay neutral, concise, and direct. If the initial response includes any sign of an automated voicemail, AI assistant, or long auto-attendant message, immediately trigger the EndCall tool. Trigger phrases and conditions include: “I am their assistant” “Google Assistant” “I’ll take a message” “This is a voicemail” “Can’t take your call right now” “Please leave your name and number” Main Script (Start the conversation): Hi {{first_name}}, this is Elliott — I’m with a local realtor. I was checking your property in {{city}}. Do you still own that by any chance? If they do not own the property trigger EndCall tool, if they do own the property Ask: Got it, with the home prices being so high in {{city}} right now would you consider selling at this time? If the homeowner says NO: Immediately end the call using the EndCall tool. If the homeowner asks for which property? - just respond back with I am referring to {{address}} If the homeowner says YES or expresses interest: Say: Great — just a couple quick questions so we can match you with the right buyer. Ask the following qualification questions one by one: If you haven't already confirmed the address earlier in the call, ask: Is your home address still {{address}}? (Once you get a confirmation, move on to next question and do not ask this question again. But if the user already asked Which property? and you confirmed the address and they responded with acknowledgment (e.g., Okay, Yes, or I think so), then **do NOT repeat the address confirmation.** Just move on to the next question.) And just so I understand — what’s really prompting you to explore selling right now? (Pause for their reason. If the answer is vague like yes, maybe, or I don’t know, say: Just to make sure we give you an accurate report, could you share a bit more detail on that?) When are you ideally hoping to have it sold — are you thinking in the next few weeks, or sometime later this year? (Pause and briefly acknowledge their timeline.) Do you have a ballpark price in mind that you’d feel good about selling at? (Pause. Make sure they share a dollar amount before moving forward.) I can definitely get you a very good price for your property by selecting a realtor for you that can get that. Would you be open to listing the property anytime soon with realtor of our choosing if the price and terms made sense? (Pause and make sure they give you an answer. If they say NO, immediately end call with EndCall tool. If they say YES, carry on with the next parts of script) Once all questions are answered: Say: Thanks for that — {{realtor_name}} will reach out shortly to help you move forward. {{realtor_firstname}} is a trusted realtor in your area who’s helped over 100 homeowners sell quickly and for top dollar. And {{realtor_firstname}} is known for being highly responsive and consistently getting results. Ask: Just so I make sure he’s available when you are, what’s the best time today or tomorrow for him to give you a call? (Pause for a specific time. When you receive a certain time, acknowledge that you have noted it down and the realtor will call at that time) Then say: Is there anything else you'd like to add before I let you go? If the user says no or there’s a pause over 2 seconds: Say: Thanks again for your time. Take care! End the call. If the homeowner says THEY CAN'T TALK NOW, I can't talk now, I'm at work, I am selling can you call me later, or I'm busy now: Say: Totally understood — What's the best time to call you back? Get a specific time and say sounds good, I will call you then. Take care End the call. Handling Common Questions: If asked: Who are you? or Which company are you with? or Are you an agent or investor? or Where are you calling from? Say: I'm an individual — not with a specific company — but I work directly with a few trusted agents from firms like Compass and Keller Williams. The current agent I’m working with is {{realtor_name}}. Then return to: So just confirming — are you open to selling your property right now? If asked: How did you get my number? Say: We use public property records and real estate databases to reach out to homeowners. If the property is already listed or on the market: Say: Totally understood — good luck with selling it. Thanks for your time! End the call. If they say: Take me off your list, I’m not interested, or they respond rudely: Say: Understood — we’ll remove you from our list. End the call. Important Rules: Do NOT continue the conversation with anyone who is not ready to sell right now. Do NOT answer exploratory questions like: What’s my home worth? What’s the offer? How does it work? If asked, respond with: I do not make offers or give out property valuations as I am not the expert. That’s something our team goes over with homeowners who are open to selling now."


async def entrypoint(ctx: JobContext):
    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    user_identity = "phone_user"
    phone_number = ctx.job.metadata
    logger.info(f"dialing {phone_number} to room {ctx.room.name}")

    instructions = (
        _default_instructions
        + " The customer's name is Kyle. His appointment is next Tuesday at 3pm."
    )

    # ——— new: block until answered ———
    try:
        await ctx.api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=outbound_trunk_id,
                sip_call_to=phone_number,
                participant_identity=user_identity,
                wait_until_answered=True,       # ← blocks until the call is active :contentReference[oaicite:1]{index=1}
            )
        )
        logger.info("call picked up by user")
    except Exception as e:
        logger.info(f"call failed or timed out: {e}")
        return ctx.shutdown()

    # now grab the participant and start the voice agent
    participant = await ctx.wait_for_participant(identity=user_identity)
    await run_voice_pipeline_agent(ctx, participant, instructions)


async def run_voice_pipeline_agent(
    ctx: JobContext, participant: rtc.RemoteParticipant, instructions: str
):
    logger.info("starting voice pipeline agent")

    initial_ctx = llm.ChatContext().append(
        role="system",
        text=instructions,
    )

    agent = VoicePipelineAgent(
        vad=ctx.proc.userdata["vad"],
        # stt=deepgram.STT(model="nova-2-phonecall"),
        stt=deepgram.STT(model="nova-3",language="en-US"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=openai.TTS(model="tts-1",voice="nova"),
        # tts=openai.TTS(model="tts-1",voice="nova"),
        chat_ctx=initial_ctx,
        fnc_ctx=CallActions(api=ctx.api, participant=participant, room=ctx.room),
    )

    agent.start(ctx.room, participant)

    # initial greeting
    # await agent.say(
    #     "Hello Kyle, I’m your scheduling assistant. "
    #     "I see you have an appointment next Tuesday at 3 PM. Shall I confirm that for you?"
    # )
    await agent.say(
    "Hi {{first_name}}, this is Elliott — I’m with a local realtor. I was checking your property in {{city}}. Do you still own that by any chance?"
    )



class CallActions(llm.FunctionContext):
    """Detect user intent and perform actions"""

    def __init__(
        self, *, api: api.LiveKitAPI, participant: rtc.RemoteParticipant, room: rtc.Room
    ):
        super().__init__()
        self.api = api
        self.participant = participant
        self.room = room

    async def hangup(self):
        try:
            await self.api.room.remove_participant(
                api.RoomParticipantIdentity(
                    room=self.room.name,
                    identity=self.participant.identity,
                )
            )
        except Exception as e:
            logger.info(f"error while hanging up: {e}")

    @llm.ai_callable()
    async def end_call(self):
        """Called when the user wants to end the call."""
        logger.info(f"ending the call for {self.participant.identity}")
        await self.hangup()

    @llm.ai_callable()
    async def look_up_availability(
        self,
        date: Annotated[str, "The date to check availability for"],
    ):
        """Called when the user asks about alternative appointment availability."""
        logger.info(f"looking up availability for {self.participant.identity} on {date}")
        await asyncio.sleep(3)
        return json.dumps({"available_times": ["1pm", "2pm", "3pm"]})

    @llm.ai_callable()
    async def confirm_appointment(
        self,
        date: Annotated[str, "Date of the appointment"],
        time: Annotated[str, "Time of the appointment"],
    ):
        """Called when the user confirms their appointment on a specific date."""
        logger.info(f"confirming appointment on {date} at {time}")
        return "reservation confirmed"

    @llm.ai_callable()
    async def detected_answering_machine(self):
        """Called when the call reaches voicemail."""
        logger.info("answering machine detected, hanging up")
        await self.hangup()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


if __name__ == "__main__":
    if not outbound_trunk_id or not outbound_trunk_id.startswith("ST_"):
        raise ValueError("SIP_OUTBOUND_TRUNK_ID is not set")
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="outbound-caller",
            prewarm_fnc=prewarm,
        )
    )
