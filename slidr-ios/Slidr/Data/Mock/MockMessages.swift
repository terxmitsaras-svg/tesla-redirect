import Foundation

struct MockMessages {

    static func minutesAgo(_ m: Double) -> Date {
        Date().addingTimeInterval(-m * 60)
    }

    static func hoursAgo(_ h: Double) -> Date {
        Date().addingTimeInterval(-h * 3600)
    }

    static let all: [String: [Message]] = [
        "1": [
            Message(id: "1-1", fromUserId: "1", toUserId: "me", text: "Hey, what's up?", timestamp: minutesAgo(62), isRead: true),
            Message(id: "1-2", fromUserId: "me", toUserId: "1", text: "Not much, just finished work. You?", timestamp: minutesAgo(60), isRead: true),
            Message(id: "1-3", fromUserId: "1", toUserId: "me", text: "Same. Was thinking about hitting the gym later. Wanna join?", timestamp: minutesAgo(58), isRead: true),
            Message(id: "1-4", fromUserId: "me", toUserId: "1", text: "Sounds good, what time?", timestamp: minutesAgo(30), isRead: true),
            Message(id: "1-5", fromUserId: "1", toUserId: "me", text: "Around 7? We could grab food after", timestamp: minutesAgo(28), isRead: true),
            Message(id: "1-6", fromUserId: "me", toUserId: "1", text: "Perfect. I'm in.", timestamp: minutesAgo(25), isRead: true),
            Message(id: "1-7", fromUserId: "1", toUserId: "me", text: "Nice. See you there 💪", timestamp: minutesAgo(2), isRead: false)
        ],
        "2": [
            Message(id: "2-1", fromUserId: "2", toUserId: "me", text: "Loved your profile! Are you into indie music?", timestamp: hoursAgo(5), isRead: true),
            Message(id: "2-2", fromUserId: "me", toUserId: "2", text: "Huge fan actually. What are you listening to lately?", timestamp: hoursAgo(4), isRead: true),
            Message(id: "2-3", fromUserId: "2", toUserId: "me", text: "Been obsessed with Ethel Cain lately. You know her?", timestamp: hoursAgo(3), isRead: true),
            Message(id: "2-4", fromUserId: "me", toUserId: "2", text: "Yes! Her album is a masterpiece", timestamp: hoursAgo(2), isRead: true),
            Message(id: "2-5", fromUserId: "2", toUserId: "me", text: "Right?! Okay you pass the vibe check lol", timestamp: hoursAgo(1), isRead: true),
            Message(id: "2-6", fromUserId: "me", toUserId: "2", text: "Ha! What are you up to this weekend?", timestamp: minutesAgo(45), isRead: true),
            Message(id: "2-7", fromUserId: "2", toUserId: "me", text: "DJing at The Loft on Saturday. You should come", timestamp: minutesAgo(10), isRead: false),
            Message(id: "2-8", fromUserId: "2", toUserId: "me", text: "I can put you on the list", timestamp: minutesAgo(9), isRead: false)
        ],
        "7": [
            Message(id: "7-1", fromUserId: "7", toUserId: "me", text: "Long shift finally done. You around?", timestamp: minutesAgo(90), isRead: true),
            Message(id: "7-2", fromUserId: "me", toUserId: "7", text: "Yeah just chilling. Rough night?", timestamp: minutesAgo(88), isRead: true),
            Message(id: "7-3", fromUserId: "7", toUserId: "me", text: "You have no idea. Need to decompress badly", timestamp: minutesAgo(85), isRead: true),
            Message(id: "7-4", fromUserId: "me", toUserId: "7", text: "I know a good way to do that 😏", timestamp: minutesAgo(80), isRead: true),
            Message(id: "7-5", fromUserId: "7", toUserId: "me", text: "Oh yeah? Tell me more", timestamp: minutesAgo(78), isRead: true),
            Message(id: "7-6", fromUserId: "me", toUserId: "7", text: "Come over. I'll make drinks", timestamp: minutesAgo(70), isRead: true),
            Message(id: "7-7", fromUserId: "7", toUserId: "me", text: "Give me 20 minutes", timestamp: minutesAgo(5), isRead: false)
        ]
    ]

    static var conversations: [Conversation] {
        all.compactMap { (userId, messages) -> Conversation? in
            guard let last = messages.last else { return nil }
            let unread = messages.filter { !$0.isRead && $0.fromUserId != "me" }.count
            return Conversation(
                id: userId,
                lastMessage: last.text,
                lastMessageTime: last.timestamp,
                unreadCount: unread
            )
        }.sorted { $0.lastMessageTime > $1.lastMessageTime }
    }
}
