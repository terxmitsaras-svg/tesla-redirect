import Foundation

struct Message: Identifiable, Equatable {
    let id: String
    let fromUserId: String
    let toUserId: String
    let text: String
    let timestamp: Date
    var isRead: Bool

    var isSent: Bool { fromUserId == "me" }

    var timeLabel: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "h:mm a"
        return formatter.string(from: timestamp)
    }
}

struct Conversation: Identifiable {
    let id: String          // userId of the other person
    var lastMessage: String
    var lastMessageTime: Date
    var unreadCount: Int

    var timeLabel: String {
        let diff = Date().timeIntervalSince(lastMessageTime)
        if diff < 60 { return "now" }
        if diff < 3600 { return "\(Int(diff / 60))m" }
        if diff < 86400 { return "\(Int(diff / 3600))h" }
        return "\(Int(diff / 86400))d"
    }
}
