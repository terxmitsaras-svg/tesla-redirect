#include <gtest/gtest.h>
#include "string_utils.h"

using namespace posokanei;

// ── normalizeGreek ────────────────────────────────────────────────────────

TEST(NormalizeGreek, Empty) {
    EXPECT_EQ("", normalizeGreek(""));
}

TEST(NormalizeGreek, AlreadyLowercase) {
    EXPECT_EQ("αβγδ", normalizeGreek("αβγδ"));
}

TEST(NormalizeGreek, UppercaseToLower) {
    EXPECT_EQ("αβγδεζηθ", normalizeGreek("ΑΒΓΔΕΖΗΘ"));
    EXPECT_EQ("ικλμνξοπ", normalizeGreek("ΙΚΛΜΝΞΟΠ"));
    EXPECT_EQ("ρστυφχψω", normalizeGreek("ΡΣΤΥΦΧΨΩ"));
}

TEST(NormalizeGreek, StressMarkRemoved) {
    EXPECT_EQ("α", normalizeGreek("ά"));
    EXPECT_EQ("ε", normalizeGreek("έ"));
    EXPECT_EQ("η", normalizeGreek("ή"));
    EXPECT_EQ("ι", normalizeGreek("ί"));
    EXPECT_EQ("ο", normalizeGreek("ό"));
    EXPECT_EQ("υ", normalizeGreek("ύ"));
    EXPECT_EQ("ω", normalizeGreek("ώ"));
}

TEST(NormalizeGreek, UppercaseAccentedToLowerBase) {
    EXPECT_EQ("α", normalizeGreek("Ά"));
    EXPECT_EQ("ε", normalizeGreek("Έ"));
    EXPECT_EQ("η", normalizeGreek("Ή"));
    EXPECT_EQ("ι", normalizeGreek("Ί"));
    EXPECT_EQ("ο", normalizeGreek("Ό"));
    EXPECT_EQ("υ", normalizeGreek("Ύ"));
    EXPECT_EQ("ω", normalizeGreek("Ώ"));
}

TEST(NormalizeGreek, DialytikaRemoved) {
    EXPECT_EQ("ι", normalizeGreek("ϊ"));  // dialytika only
    EXPECT_EQ("υ", normalizeGreek("ϋ"));
    EXPECT_EQ("ι", normalizeGreek("ΐ"));  // dialytika + tonos
    EXPECT_EQ("υ", normalizeGreek("ΰ"));
    EXPECT_EQ("ι", normalizeGreek("Ϊ"));  // uppercase with dialytika
    EXPECT_EQ("υ", normalizeGreek("Ϋ"));
}

TEST(NormalizeGreek, RealWords) {
    EXPECT_EQ("γαλα",       normalizeGreek("Γάλα"));
    EXPECT_EQ("ελαιολαδο",  normalizeGreek("Ελαιόλαδο"));
    EXPECT_EQ("κοτοπουλο",  normalizeGreek("Κοτόπουλο"));
    EXPECT_EQ("σπαγγετι",   normalizeGreek("Σπαγγέτι"));
    EXPECT_EQ("ντοματες",   normalizeGreek("Ντομάτες"));
    EXPECT_EQ("φετα",       normalizeGreek("Φέτα"));
    EXPECT_EQ("ζαχαρη",     normalizeGreek("Ζάχαρη"));
    EXPECT_EQ("αλευρι",     normalizeGreek("Αλεύρι"));
}

TEST(NormalizeGreek, AsciiLowercased) {
    EXPECT_EQ("abc", normalizeGreek("ABC"));
    EXPECT_EQ("xyz", normalizeGreek("xyz"));
}

TEST(NormalizeGreek, MixedGreekAscii) {
    EXPECT_EQ("abc αβγ", normalizeGreek("ABC ΑΒΓ"));
    EXPECT_EQ("γαλα 1l", normalizeGreek("Γάλα 1L"));
}

// ── containsNormalized ────────────────────────────────────────────────────

TEST(ContainsNormalized, ExactMatch) {
    EXPECT_TRUE(containsNormalized("γάλα", "γάλα"));
}

TEST(ContainsNormalized, IgnoresAccents) {
    EXPECT_TRUE(containsNormalized("Γάλα Πλήρες 1L", "γαλα"));
    EXPECT_TRUE(containsNormalized("Ελαιόλαδο Παρθένο", "ελαιολαδο"));
}

TEST(ContainsNormalized, CaseInsensitive) {
    EXPECT_TRUE(containsNormalized("ΚΟΤΟΠΟΥΛΟ ΦΙΛΕΤΟ", "κοτόπουλο"));
    EXPECT_TRUE(containsNormalized("φέτα", "ΦΕΤΑ"));
}

TEST(ContainsNormalized, PartialMatch) {
    EXPECT_TRUE(containsNormalized("Κρέμα Γάλακτος 200ml", "γαλα"));
    EXPECT_TRUE(containsNormalized("Μπριζόλες Χοιρινές", "χοιρ"));
}

TEST(ContainsNormalized, NoMatch) {
    EXPECT_FALSE(containsNormalized("Γάλα", "καφες"));
    EXPECT_FALSE(containsNormalized("Ψωμί", "γαλα"));
}

TEST(ContainsNormalized, EmptyNeedle) {
    EXPECT_TRUE(containsNormalized("anything", ""));
    EXPECT_TRUE(containsNormalized("", ""));
}

TEST(ContainsNormalized, EmptyHaystack) {
    EXPECT_FALSE(containsNormalized("", "γαλα"));
}
