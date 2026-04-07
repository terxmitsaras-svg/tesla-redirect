package com.slidr.app.data.mock

import com.slidr.app.data.model.Message

object MockMessages {

    private val now = System.currentTimeMillis()
    private fun minutesAgo(m: Long) = now - m * 60_000
    private fun hoursAgo(h: Long) = now - h * 3_600_000

    val MESSAGES: Map<String, List<Message>> = mapOf(
        "1" to listOf(
            Message("1-1", "1", "me", "Hey, what's up?", minutesAgo(62), true),
            Message("1-2", "me", "1", "Not much, just finished work. You?", minutesAgo(60), true),
            Message("1-3", "1", "me", "Same. Was thinking about hitting the gym later. Wanna join?", minutesAgo(58), true),
            Message("1-4", "me", "1", "Sounds good, what time?", minutesAgo(30), true),
            Message("1-5", "1", "me", "Around 7? We could grab food after", minutesAgo(28), true),
            Message("1-6", "me", "1", "Perfect. I'm in.", minutesAgo(25), true),
            Message("1-7", "1", "me", "Nice. See you there 💪", minutesAgo(2), false)
        ),
        "2" to listOf(
            Message("2-1", "2", "me", "Loved your profile! Are you into indie music?", hoursAgo(5), true),
            Message("2-2", "me", "2", "Huge fan actually. What are you listening to lately?", hoursAgo(4), true),
            Message("2-3", "2", "me", "Been obsessed with Ethel Cain lately. You know her?", hoursAgo(3), true),
            Message("2-4", "me", "2", "Yes! Her album is a masterpiece", hoursAgo(2), true),
            Message("2-5", "2", "me", "Right?! Okay you pass the vibe check lol", hoursAgo(1), true),
            Message("2-6", "me", "2", "Ha! What are you up to this weekend?", minutesAgo(45), true),
            Message("2-7", "2", "me", "DJing at The Loft on Saturday. You should come", minutesAgo(10), false),
            Message("2-8", "2", "me", "I can put you on the list", minutesAgo(9), false)
        ),
        "3" to listOf(
            Message("3-1", "me", "3", "Hey! Fellow software person here 👋", hoursAgo(25), true),
            Message("3-2", "3", "me", "Oh nice, what stack do you work in?", hoursAgo(24), true),
            Message("3-3", "me", "3", "Mostly backend. Kotlin actually lol", hoursAgo(23), true),
            Message("3-4", "3", "me", "No way, me too! Which framework?", hoursAgo(20), true),
            Message("3-5", "me", "3", "Spring Boot mostly. You?", hoursAgo(18), true),
            Message("3-6", "3", "me", "Same. We should compare notes sometime. Over coffee?", hoursAgo(2), false),
            Message("3-7", "3", "me", "Or something stronger if you're game", hoursAgo(1), false)
        ),
        "7" to listOf(
            Message("7-1", "7", "me", "Long shift finally done. You around?", minutesAgo(90), true),
            Message("7-2", "me", "7", "Yeah just chilling. Rough night?", minutesAgo(88), true),
            Message("7-3", "7", "me", "You have no idea. Need to decompress badly", minutesAgo(85), true),
            Message("7-4", "me", "7", "I know a good way to do that 😏", minutesAgo(80), true),
            Message("7-5", "7", "me", "Oh yeah? Tell me more", minutesAgo(78), true),
            Message("7-6", "me", "7", "Come over. I'll make drinks", minutesAgo(70), true),
            Message("7-7", "7", "me", "Give me 20 minutes", minutesAgo(5), false)
        ),
        "10" to listOf(
            Message("10-1", "10", "me", "Yo your taste in music is actually fire 🔥", hoursAgo(10), true),
            Message("10-2", "me", "10", "Ha thanks! I try. What genre you produce?", hoursAgo(9), true),
            Message("10-3", "10", "me", "Mostly house and techno. Bit of R&B on the side", hoursAgo(8), true),
            Message("10-4", "me", "10", "That's a sick combo. Would love to hear some tracks", hoursAgo(6), true),
            Message("10-5", "10", "me", "Come by the studio sometime. I'll play you some unreleased stuff", hoursAgo(4), true),
            Message("10-6", "me", "10", "When?", minutesAgo(120), true),
            Message("10-7", "10", "me", "You around Thursday?", minutesAgo(15), false)
        )
    )
}
