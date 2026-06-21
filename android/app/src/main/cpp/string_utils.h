#pragma once
#include <string>

namespace posokanei {

// Normalize UTF-8 Greek text for search:
//   - uppercase letters lowercased (Α→α, Β→β, …)
//   - monotonic stress marks removed (ά→α, έ→ε, ή→η, ί→ι, ό→ο, ύ→υ, ώ→ω)
//   - dialytika removed (ϊ→ι, ϋ→υ, ΐ→ι, ΰ→υ)
//   - ASCII lowercased via std::tolower
// Non-Greek multibyte sequences are passed through unchanged.
std::string normalizeGreek(const std::string& utf8_text);

// True if haystack contains needle after both are normalizeGreek'd.
bool containsNormalized(const std::string& haystack, const std::string& needle);

} // namespace posokanei
