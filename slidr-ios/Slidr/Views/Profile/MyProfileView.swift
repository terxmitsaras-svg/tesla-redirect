import SwiftUI

struct MyProfileView: View {
    @EnvironmentObject var userRepo: UserRepository
    @State private var showSettings = false

    var me: User { userRepo.currentUser }

    var body: some View {
        NavigationStack {
            ZStack {
                Color.slidrBackground.ignoresSafeArea()

                ScrollView {
                    VStack(alignment: .leading, spacing: 0) {
                        Spacer().frame(height: 20)

                        // Avatar
                        HStack {
                            ZStack(alignment: .bottomTrailing) {
                                ProfileImage(url: me.avatarURL, size: 100, showBorder: true)
                                Circle()
                                    .fill(Color.slidrFuchsia)
                                    .frame(width: 30, height: 30)
                                    .overlay(Image(systemName: "pencil").font(.system(size: 13, weight: .bold)).foregroundColor(.white))
                            }
                            VStack(alignment: .leading, spacing: 4) {
                                Text("\(me.displayName), \(me.age)")
                                    .font(.system(size: 22, weight: .bold))
                                    .foregroundColor(.white)
                                Text(me.pronouns)
                                    .font(.system(size: 13))
                                    .foregroundColor(.slidrTextSecond)
                            }
                            .padding(.leading, 16)
                        }
                        .padding(.horizontal, 20)

                        Spacer().frame(height: 20)
                        Divider().background(Color.slidrDivider).padding(.horizontal, 20)

                        // Bio
                        ProfileSection(title: "Bio") {
                            Text(me.bio)
                                .font(.system(size: 15))
                                .foregroundColor(.white.opacity(0.9))
                                .lineSpacing(5)
                        }

                        Divider().background(Color.slidrDivider).padding(.horizontal, 20)

                        // Stats
                        HStack {
                            Spacer()
                            StatCell(label: "Height", value: me.height)
                            Spacer()
                            StatCell(label: "Body", value: me.bodyType)
                            Spacer()
                        }
                        .padding(.vertical, 16)

                        Divider().background(Color.slidrDivider).padding(.horizontal, 20)

                        ProfileSection(title: "Looking for") {
                            FlowLayout(spacing: 8) {
                                ForEach(me.lookingFor, id: \.self) { item in TagChip(text: item, selected: true) }
                            }
                        }

                        if !me.tags.isEmpty {
                            Divider().background(Color.slidrDivider).padding(.horizontal, 20)
                            ProfileSection(title: "Tags") {
                                FlowLayout(spacing: 8) {
                                    ForEach(me.tags, id: \.self) { tag in TagChip(text: tag) }
                                }
                            }
                        }

                        Spacer().frame(height: 40)
                    }
                }
            }
            .navigationTitle("My Profile")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(Color.slidrBackground, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button { showSettings = true } label: {
                        Image(systemName: "gearshape").foregroundColor(.white)
                    }
                }
            }
            .navigationDestination(isPresented: $showSettings) {
                SettingsView()
            }
        }
    }
}

struct ProfileSection<Content: View>: View {
    let title: String
    @ViewBuilder let content: () -> Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title.uppercased())
                .font(.system(size: 11, weight: .medium))
                .foregroundColor(.slidrTextSecond)
                .tracking(1.5)
            content()
        }
        .padding(20)
    }
}
