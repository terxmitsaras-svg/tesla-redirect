#include <gtest/gtest.h>
#include "price_utils.h"

using namespace posokanei;

// ── parsePrice ─────────────────────────────────────────────────────────────

TEST(ParsePrice, EuropeanDecimalComma) {
    EXPECT_DOUBLE_EQ(2.49,  parsePrice("2,49 €"));
    EXPECT_DOUBLE_EQ(1.00,  parsePrice("1,00"));
    EXPECT_DOUBLE_EQ(3.50,  parsePrice("3,50€/kg"));
    EXPECT_DOUBLE_EQ(0.99,  parsePrice("0,99"));
}

TEST(ParsePrice, PeriodDecimalSeparator) {
    EXPECT_DOUBLE_EQ(2.49,  parsePrice("2.49"));
    EXPECT_DOUBLE_EQ(1.99,  parsePrice("1.99 €"));
    EXPECT_DOUBLE_EQ(10.5,  parsePrice("10.5"));
}

TEST(ParsePrice, EuropeanThousandsSeparator) {
    EXPECT_DOUBLE_EQ(1234.56, parsePrice("1.234,56 €"));
    EXPECT_DOUBLE_EQ(10000.0, parsePrice("10.000,00"));
    EXPECT_DOUBLE_EQ(1000.0,  parsePrice("1.000"));
}

TEST(ParsePrice, AngloThousandsSeparator) {
    EXPECT_DOUBLE_EQ(1234.56, parsePrice("1,234.56"));
    EXPECT_DOUBLE_EQ(1000.0,  parsePrice("1,000"));
}

TEST(ParsePrice, Integer) {
    EXPECT_DOUBLE_EQ(5.0,  parsePrice("5 €"));
    EXPECT_DOUBLE_EQ(12.0, parsePrice("12"));
}

TEST(ParsePrice, LeadingText) {
    EXPECT_DOUBLE_EQ(2.49, parsePrice("Τιμή: 2,49€"));
    EXPECT_DOUBLE_EQ(3.99, parsePrice("από 3,99 €"));
}

TEST(ParsePrice, TrailingSuffix) {
    EXPECT_DOUBLE_EQ(3.50, parsePrice("3,50 €/kg"));
    EXPECT_DOUBLE_EQ(2.20, parsePrice("2,20€ / τεμ."));
}

TEST(ParsePrice, Invalid) {
    EXPECT_DOUBLE_EQ(-1.0, parsePrice(""));
    EXPECT_DOUBLE_EQ(-1.0, parsePrice("€"));
    EXPECT_DOUBLE_EQ(-1.0, parsePrice("δεν βρέθηκε τιμή"));
    EXPECT_DOUBLE_EQ(-1.0, parsePrice("N/A"));
}

// ── formatPrice ───────────────────────────────────────────────────────────

TEST(FormatPrice, Standard) {
    EXPECT_EQ("2,49 €",  formatPrice(2.49));
    EXPECT_EQ("10,00 €", formatPrice(10.0));
    EXPECT_EQ("0,99 €",  formatPrice(0.99));
    EXPECT_EQ("1,00 €",  formatPrice(1.0));
}

TEST(FormatPrice, RoundTrip) {
    // format then parse must recover the original value
    const double price = 3.75;
    EXPECT_DOUBLE_EQ(price, parsePrice(formatPrice(price)));
}

// ── findCheapestIndex ─────────────────────────────────────────────────────

TEST(FindCheapestIndex, Empty) {
    EXPECT_EQ(-1, findCheapestIndex({}));
}

TEST(FindCheapestIndex, Single) {
    EXPECT_EQ(0, findCheapestIndex({5.99}));
}

TEST(FindCheapestIndex, First) {
    EXPECT_EQ(0, findCheapestIndex({1.0, 2.0, 3.0}));
}

TEST(FindCheapestIndex, Last) {
    EXPECT_EQ(2, findCheapestIndex({3.0, 2.0, 1.0}));
}

TEST(FindCheapestIndex, Middle) {
    EXPECT_EQ(1, findCheapestIndex({3.0, 1.5, 2.5}));
}

TEST(FindCheapestIndex, Equal) {
    // When tied, first occurrence wins (std::min_element guarantee)
    EXPECT_EQ(0, findCheapestIndex({1.0, 1.0, 1.0}));
}
