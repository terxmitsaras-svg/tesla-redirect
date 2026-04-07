import SwiftUI

struct ProfileImage: View {
    let url: String
    var size: CGFloat = 48
    var isOnline: Bool = false
    var showBorder: Bool = false

    var body: some View {
        ZStack(alignment: .bottomTrailing) {
            AsyncImage(url: URL(string: url)) { img in
                img.resizable().scaledToFill()
            } placeholder: {
                Circle().fill(Color.slidrSurfaceVar)
                    .overlay(Image(systemName: "person.fill").foregroundColor(.slidrTextSecond))
            }
            .frame(width: size, height: size)
            .clipShape(Circle())
            .overlay(showBorder ? Circle().stroke(Color.slidrFuchsia, lineWidth: 2) : nil)

            if isOnline {
                Circle()
                    .fill(Color.slidrOnline)
                    .frame(width: size * 0.22, height: size * 0.22)
                    .overlay(Circle().stroke(Color.black, lineWidth: 1.5))
            }
        }
    }
}
