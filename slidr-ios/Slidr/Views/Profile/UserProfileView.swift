import SwiftUI

struct UserProfileView: View {
    let user: User
    @EnvironmentObject var userRepo: UserRepository
    @EnvironmentObject var messageRepo: MessageRepository
    @Environment(\.dismiss) var dismiss
    @State private var navigateToChat = false

    var currentUser: User {
        userRepo.nearbyUsers.first { $0.id == user.id } ?? user
    }

    var body: some View {
        ZStack(alignment: .top) {
            Color.slidrBackground.ignoresSafeArea()

            ScrollView {
                VStack(spacing: 0) {
                    // Hero photo
                    AsyncImage(url: URL(string: user.avatarURL)) { img in
                        img.resizable().scaledToFill()
                    } placeholder: {
                        Rectangle().fill(Color.slidrSurfaceVar)
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 360)
                    .clipped()

                    // Content
                    VStack(alignment: .leading, spacing: 0) {
                        // Name + pronouns row
                        HStack(alignment: .top) {
                            VStack(alignment: .leading, spacing: 4) {
                                Text("\(user.displayName), \(user.age)")
                                    .font(.system(size: 26, weight: .bold))
                                    .foregroundColor(.white)
                                HStack(spacing: 4) {
                                    if user.isOnline {
                                        Image(systemName: "wifi")
                                            .font(.system(size: 12))
                                            .foregroundColor(.slidrOnline)
                                        Text("Online now")
                                            .font(.system(size: 13))
                                            .foregroundColor(.slidrOnline)
                                    } else {
                                        Image(systemName: "location")
                                            .font(.system(size: 12))
                                            .foregroundColor(.slidrTextSecond)
                                        Text("\(user.distanceLabel) away")
                                            .font(.system(size: 13))
                                            .foregroundColor(.slidrTextSecond)
                                    }
                                }
                            }
                            Spacer()
                            Text(user.pronouns)
                                .font(.system(size: 13))
                                .foregroundColor(.slidrTextSecond)
                                .padding(.horizontal, 10)
                                .padding(.vertical, 4)
                                .background(Color.slidrSurfaceVar)
                                .cornerRadius(6)
                        }
                        .padding(20)

                        Divider().background(Color.slidrDivider).padding(.horizontal, 20)

                        // Bio
                        Text(user.bio)
                            .font(.system(size: 15))
                            .foregroundColor(.white.opacity(0.9))
                            .lineSpacing(6)
                            .padding(20)

                        Divider().background(Color.slidrDivider).padding(.horizontal, 20)

                        // Stats
                        HStack {
                            Spacer()
                            StatCell(label: "Height", value: user.height)
                            Spacer()
                            StatCell(label: "Body", value: user.bodyType)
                            Spacer()
                        }
                        .padding(.vertical, 16)

                        Divider().background(Color.slidrDivider).padding(.horizontal, 20)

                        // Looking for
                        VStack(alignment: .leading, spacing: 10) {
                            Text("LOOKING FOR")
                                .font(.system(size: 11, weight: .medium))
                                .foregroundColor(.slidrTextSecond)
                                .tracking(1.5)

                            FlowLayout(spacing: 8) {
                                ForEach(user.lookingFor, id: \.self) { item in
                                    TagChip(text: item, selected: true)
                                }
                            }
                        }
                        .padding(20)

                        if !user.tags.isEmpty {
                            Divider().background(Color.slidrDivider).padding(.horizontal, 20)
                            VStack(alignment: .leading, spacing: 10) {
                                Text("VIBE")
                                    .font(.system(size: 11, weight: .medium))
                                    .foregroundColor(.slidrTextSecond)
                                    .tracking(1.5)
                                FlowLayout(spacing: 8) {
                                    ForEach(user.tags, id: \.self) { tag in
                                        TagChip(text: tag)
                                    }
                                }
                            }
                            .padding(20)
                        }

                        Divider().background(Color.slidrDivider).padding(.horizontal, 20)

                        // Action buttons
                        HStack(spacing: 12) {
                            Button {
                                messageRepo.startConversation(with: user.id)
                                navigateToChat = true
                            } label: {
                                Text("Message")
                                    .font(.system(size: 16, weight: .bold))
                                    .foregroundColor(.white)
                                    .frame(maxWidth: .infinity)
                                    .frame(height: 52)
                                    .background(Color.slidrFuchsia)
                                    .cornerRadius(12)
                            }

                            Button {
                                userRepo.toggleFavorite(userId: user.id)
                            } label: {
                                HStack(spacing: 6) {
                                    Image(systemName: currentUser.isFavorite ? "heart.fill" : "heart")
                                    Text(currentUser.isFavorite ? "Saved" : "Save")
                                }
                                .font(.system(size: 15, weight: .medium))
                                .foregroundColor(.slidrFuchsia)
                                .frame(height: 52)
                                .padding(.horizontal, 16)
                                .overlay(RoundedRectangle(cornerRadius: 12)
                                    .stroke(Color.slidrFuchsia, lineWidth: 1))
                            }
                        }
                        .padding(20)
                        .padding(.bottom, 20)
                    }
                }
            }
            .ignoresSafeArea(edges: .top)

            // Back button overlay
            HStack {
                Button { dismiss() } label: {
                    Image(systemName: "chevron.left")
                        .font(.system(size: 17, weight: .semibold))
                        .foregroundColor(.white)
                        .frame(width: 40, height: 40)
                        .background(Color.black.opacity(0.4))
                        .clipShape(Circle())
                }
                .padding(.leading, 16)
                .padding(.top, 60)
                Spacer()
            }

            // Navigation to chat
            NavigationLink(destination: ChatView(userId: user.id), isActive: $navigateToChat) {
                EmptyView()
            }
        }
        .navigationBarHidden(true)
    }
}

struct StatCell: View {
    let label: String
    let value: String

    var body: some View {
        VStack(spacing: 2) {
            Text(label)
                .font(.system(size: 12))
                .foregroundColor(.slidrTextSecond)
            Text(value)
                .font(.system(size: 15, weight: .semibold))
                .foregroundColor(.white)
        }
    }
}
