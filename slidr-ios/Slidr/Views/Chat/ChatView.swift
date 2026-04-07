import SwiftUI

struct ChatView: View {
    let userId: String
    @EnvironmentObject var messageRepo: MessageRepository
    @EnvironmentObject var userRepo: UserRepository
    @Environment(\.dismiss) var dismiss

    @State private var inputText = ""
    @State private var messages: [Message] = []

    var user: User? { userRepo.getUserById(userId) }

    var body: some View {
        VStack(spacing: 0) {
            // Messages
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 6) {
                        ForEach(messages) { message in
                            MessageBubbleView(message: message)
                                .id(message.id)
                        }
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                }
                .onChange(of: messages.count) { _, _ in
                    if let last = messages.last {
                        withAnimation { proxy.scrollTo(last.id, anchor: .bottom) }
                    }
                }
            }

            // Input bar
            HStack(spacing: 10) {
                TextField("Type a message...", text: $inputText, axis: .vertical)
                    .lineLimit(1...4)
                    .foregroundColor(.white)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                    .background(Color.slidrSurfaceVar)
                    .cornerRadius(22)

                Button {
                    let text = inputText.trimmingCharacters(in: .whitespaces)
                    guard !text.isEmpty else { return }
                    messageRepo.sendMessage(to: userId, text: text)
                    messages = messageRepo.getMessages(for: userId)
                    inputText = ""
                } label: {
                    Image(systemName: "arrow.up")
                        .font(.system(size: 16, weight: .bold))
                        .foregroundColor(inputText.trimmingCharacters(in: .whitespaces).isEmpty ? .slidrTextSecond : .white)
                        .frame(width: 40, height: 40)
                        .background(inputText.trimmingCharacters(in: .whitespaces).isEmpty ? Color.slidrSurfaceVar : Color.slidrFuchsia)
                        .clipShape(Circle())
                }
                .disabled(inputText.trimmingCharacters(in: .whitespaces).isEmpty)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(Color.slidrSurface)
        }
        .background(Color.slidrBackground)
        .navigationBarTitleDisplayMode(.inline)
        .toolbarBackground(Color.slidrSurface, for: .navigationBar)
        .toolbarBackground(.visible, for: .navigationBar)
        .toolbar {
            ToolbarItem(placement: .principal) {
                if let user {
                    HStack(spacing: 8) {
                        ProfileImage(url: user.avatarURL, size: 32, isOnline: user.isOnline)
                        VStack(alignment: .leading, spacing: 1) {
                            Text(user.displayName)
                                .font(.system(size: 15, weight: .bold))
                                .foregroundColor(.white)
                            Text(user.isOnline ? "Online now" : "Offline")
                                .font(.system(size: 11))
                                .foregroundColor(user.isOnline ? .slidrOnline : .slidrTextSecond)
                        }
                    }
                }
            }
        }
        .onAppear {
            messages = messageRepo.getMessages(for: userId)
            messageRepo.markRead(userId: userId)
        }
    }
}

struct MessageBubbleView: View {
    let message: Message

    var body: some View {
        HStack {
            if message.isSent { Spacer(minLength: 60) }
            VStack(alignment: message.isSent ? .trailing : .leading, spacing: 2) {
                Text(message.text)
                    .font(.system(size: 15))
                    .foregroundColor(.white)
                    .lineSpacing(4)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                    .background(message.isSent ? Color.slidrFuchsia : Color.slidrSurfaceVar)
                    .clipShape(
                        RoundedCornerShape(
                            radius: 18,
                            corners: message.isSent
                                ? [.topLeft, .topRight, .bottomLeft]
                                : [.topLeft, .topRight, .bottomRight]
                        )
                    )
                Text(message.timeLabel)
                    .font(.system(size: 10))
                    .foregroundColor(.slidrTextSecond)
                    .padding(.horizontal, 4)
            }
            if !message.isSent { Spacer(minLength: 60) }
        }
    }
}

struct RoundedCornerShape: Shape {
    var radius: CGFloat
    var corners: UIRectCorner

    func path(in rect: CGRect) -> Path {
        let path = UIBezierPath(
            roundedRect: rect,
            byRoundingCorners: corners,
            cornerRadii: CGSize(width: radius, height: radius)
        )
        return Path(path.cgPath)
    }
}
