import Foundation
import Combine

class MessageRepository: ObservableObject {
    @Published var messages: [String: [Message]] = MockMessages.all
    @Published var conversations: [Conversation] = MockMessages.conversations

    func getMessages(for userId: String) -> [Message] {
        messages[userId] ?? []
    }

    func sendMessage(to userId: String, text: String) {
        let newMessage = Message(
            id: UUID().uuidString,
            fromUserId: "me",
            toUserId: userId,
            text: text,
            timestamp: Date(),
            isRead: true
        )
        if messages[userId] == nil { messages[userId] = [] }
        messages[userId]?.append(newMessage)
        refreshConversations()
    }

    func startConversation(with userId: String) {
        if messages[userId] == nil {
            messages[userId] = []
            refreshConversations()
        }
    }

    func markRead(userId: String) {
        messages[userId] = messages[userId]?.map { msg in
            var m = msg; m.isRead = true; return m
        }
        refreshConversations()
    }

    private func refreshConversations() {
        conversations = messages.compactMap { (userId, msgs) -> Conversation? in
            guard let last = msgs.last else { return nil }
            let unread = msgs.filter { !$0.isRead && $0.fromUserId != "me" }.count
            return Conversation(
                id: userId,
                lastMessage: last.text,
                lastMessageTime: last.timestamp,
                unreadCount: unread
            )
        }.sorted { $0.lastMessageTime > $1.lastMessageTime }
    }

    var totalUnread: Int { conversations.reduce(0) { $0 + $1.unreadCount } }
}
