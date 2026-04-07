import SwiftUI

struct TagChip: View {
    let text: String
    var selected: Bool = false
    var action: (() -> Void)? = nil

    var body: some View {
        Button(action: { action?() }) {
            Text(text)
                .font(.system(size: 12, weight: selected ? .medium : .regular))
                .foregroundColor(selected ? .slidrFuchsia : .slidrTextSecond)
                .padding(.horizontal, 12)
                .padding(.vertical, 5)
                .background(selected ? Color.slidrFuchsia.opacity(0.15) : Color.clear)
                .overlay(
                    Capsule()
                        .stroke(selected ? Color.slidrFuchsia : Color.slidrTextSecond.opacity(0.4), lineWidth: 1)
                )
                .clipShape(Capsule())
        }
        .buttonStyle(.plain)
        .disabled(action == nil)
    }
}
