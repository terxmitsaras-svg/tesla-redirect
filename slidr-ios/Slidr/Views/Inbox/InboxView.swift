import SwiftUI

struct InboxView: View {
    @EnvironmentObject var messageRepo: MessageRepository
    @EnvironmentObject var userRepo: UserRepository

    var body: some View {
        NavigationStack {
            ZStack {
                Color.slidrBackground.ignoresSafeArea()

                if messageRepo.conversations.isEmpty {
                    VStack(spacing: 8) {
                        Text("No messages yet").foregroundColor(.slidrTextSecond).font(.system(size: 16))
                        Text("Start sliding into someone's DMs").foregroundColor(.slidrTextSecond.opacity(0.6)).font(.system(size: 13))
                    }
                } else {
                    List {
                        ForEach(messageRepo.conversations) { conversation in
                            if let user = userRepo.getUserById(conversation.id) {
                                NavigationLink(destination: ChatView(userId: conversation.id)
                                    .onAppear { messageRepo.markRead(userId: conversation.id) }
                                ) {
                                    ConversationRow(conversation: conversation, user: user)
                                }
                                .listRowBackground(
                                    conversation.unreadCount > 0 ? Color.slidrSurface : Color.slidrBackground
                                )
                                .listRowSeparatorTint(Color.slidrDivider)
                            }
                        }
                    }
                    .listStyle(.plain)
                    .background(Color.slidrBackground)
                    .scrollContentBackground(.hidden)
                }
            }
            .navigationTitle("Messages")
            .navigationBarTitleDisplayMode(.large)
            .toolbarBackground(Color.slidrBackground, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
        }
    }
}

struct ConversationRow: View {
    let conversation: Conversation
    let user: User

    var body: some View {
        HStack(spacing: 12) {
            ZStack(alignment: .topTrailing) {
                ProfileImage(url: user.avatarURL, size: 52, isOnline: user.isOnline)
                if conversation.unreadCount > 0 {
                    Text("\(conversation.unreadCount)")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(.white)
                        .padding(4)
                        .background(Color.slidrFuchsia)
                        .clipShape(Circle())
                        .offset(x: 4, y: -4)
                }
            }

            VStack(alignment: .leading, spacing: 3) {
                Text(user.displayName)
                    .font(.system(size: 15, weight: conversation.unreadCount > 0 ? .bold : .regular))
                    .foregroundColor(.white)
                Text(conversation.lastMessage)
                    .font(.system(size: 13, weight: conversation.unreadCount > 0 ? .medium : .regular))
                    .foregroundColor(conversation.unreadCount > 0 ? .white.opacity(0.85) : .slidrTextSecond)
                    .lineLimit(1)
            }

            Spacer()

            Text(conversation.timeLabel)
                .font(.system(size: 12))
                .foregroundColor(conversation.unreadCount > 0 ? .slidrFuchsia : .slidrTextSecond)
        }
        .padding(.vertical, 4)
    }
}
