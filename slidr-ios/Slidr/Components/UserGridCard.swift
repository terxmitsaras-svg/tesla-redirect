import SwiftUI

struct UserGridCard: View {
    let user: User
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            GeometryReader { geo in
                ZStack(alignment: .bottom) {
                    AsyncImage(url: URL(string: user.avatarURL)) { img in
                        img.resizable().scaledToFill()
                    } placeholder: {
                        Rectangle().fill(Color.slidrSurfaceVar)
                            .overlay(Image(systemName: "person.fill")
                                .foregroundColor(.slidrTextSecond).font(.largeTitle))
                    }
                    .frame(width: geo.size.width, height: geo.size.width)
                    .clipped()

                    // Bottom gradient scrim
                    LinearGradient(
                        colors: [.clear, .black.opacity(0.8)],
                        startPoint: .center,
                        endPoint: .bottom
                    )

                    // Name + distance overlay
                    HStack(alignment: .bottom) {
                        VStack(alignment: .leading, spacing: 1) {
                            Text("\(user.displayName), \(user.age)")
                                .font(.system(size: 12, weight: .bold))
                                .foregroundColor(.white)
                                .lineLimit(1)
                        }
                        Spacer()
                        Text(user.distanceLabel)
                            .font(.system(size: 10))
                            .foregroundColor(.white.opacity(0.8))
                    }
                    .padding(.horizontal, 6)
                    .padding(.bottom, 5)

                    // Online indicator
                    if user.isOnline {
                        VStack {
                            HStack {
                                Spacer()
                                Circle()
                                    .fill(Color.slidrOnline)
                                    .frame(width: 9, height: 9)
                                    .overlay(Circle().stroke(Color.black, lineWidth: 1.5))
                                    .padding(6)
                            }
                            Spacer()
                        }
                    }
                }
                .frame(width: geo.size.width, height: geo.size.width)
                .clipped()
            }
            .aspectRatio(1, contentMode: .fit)
        }
        .buttonStyle(.plain)
    }
}
