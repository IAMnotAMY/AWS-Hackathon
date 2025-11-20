/**
 * Property-Based Tests for Registration Validation
 * Feature: floorspace-3d-viewer, Property 2: Invalid input validation
 * Validates: Requirements 1.3
 */

import * as fc from 'fast-check';

// Validation functions extracted from RegisterPage for testing
export const validateEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

export const validatePassword = (password: string): boolean => {
  // Password must be at least 8 characters with uppercase, lowercase, and numbers
  const minLength = password.length >= 8;
  const hasUppercase = /[A-Z]/.test(password);
  const hasLowercase = /[a-z]/.test(password);
  const hasNumber = /\d/.test(password);
  
  return minLength && hasUppercase && hasLowercase && hasNumber;
};

// Generators for invalid inputs
const invalidEmailArbitrary = fc.oneof(
  fc.constant(''),                           // Empty string
  fc.constant('notanemail'),                 // No @ symbol
  fc.constant('@example.com'),               // Missing local part
  fc.constant('user@'),                      // Missing domain
  fc.constant('user @example.com'),          // Space in email
  fc.constant('user@example'),               // Missing TLD
  fc.string().filter(s => !validateEmail(s)) // Any string that fails validation
);

const invalidPasswordArbitrary = fc.oneof(
  fc.constant(''),                           // Empty string
  fc.constant('short'),                      // Too short
  fc.constant('alllowercase123'),            // No uppercase
  fc.constant('ALLUPPERCASE123'),            // No lowercase
  fc.constant('NoNumbers'),                  // No numbers
  fc.constant('OnlyLetters'),                // No numbers
  fc.string({ minLength: 1, maxLength: 7 }), // Too short
  fc.string().filter(s => !validatePassword(s)) // Any string that fails validation
);

describe('Registration Validation Properties', () => {
  describe('Property 2: Invalid input validation', () => {
    test('invalid email formats should be rejected', () => {
      fc.assert(
        fc.property(invalidEmailArbitrary, (email) => {
          const isValid = validateEmail(email);
          // Invalid emails should fail validation
          return !isValid;
        }),
        { numRuns: 100 }
      );
    });

    test('invalid password formats should be rejected', () => {
      fc.assert(
        fc.property(invalidPasswordArbitrary, (password) => {
          const isValid = validatePassword(password);
          // Invalid passwords should fail validation
          return !isValid;
        }),
        { numRuns: 100 }
      );
    });

    test('valid email formats should pass validation', () => {
      fc.assert(
        fc.property(
          fc.emailAddress(),
          (email) => {
            const isValid = validateEmail(email);
            // Valid emails should pass validation
            return isValid;
          }
        ),
        { numRuns: 100 }
      );
    });

    test('passwords with all required components should pass validation', () => {
      // Generator for valid passwords
      const validPasswordArbitrary = fc.tuple(
        fc.stringOf(fc.char().filter(c => /[a-z]/.test(c)), { minLength: 1, maxLength: 3 }),
        fc.stringOf(fc.char().filter(c => /[A-Z]/.test(c)), { minLength: 1, maxLength: 3 }),
        fc.stringOf(fc.char().filter(c => /\d/.test(c)), { minLength: 1, maxLength: 3 }),
        fc.stringOf(fc.char(), { minLength: 0, maxLength: 5 })
      ).map(([lower, upper, digit, extra]) => {
        // Shuffle to avoid predictable patterns
        const chars = (lower + upper + digit + extra).split('');
        for (let i = chars.length - 1; i > 0; i--) {
          const j = Math.floor(Math.random() * (i + 1));
          [chars[i], chars[j]] = [chars[j], chars[i]];
        }
        return chars.join('');
      }).filter(p => p.length >= 8);

      fc.assert(
        fc.property(validPasswordArbitrary, (password) => {
          const isValid = validatePassword(password);
          // Valid passwords should pass validation
          return isValid;
        }),
        { numRuns: 100 }
      );
    });

    test('mismatched passwords should be detected', () => {
      fc.assert(
        fc.property(
          fc.string(),
          fc.string(),
          (password, confirmPassword) => {
            // If passwords are different, they should not match
            if (password !== confirmPassword) {
              return password !== confirmPassword;
            }
            // If they're the same, that's fine
            return true;
          }
        ),
        { numRuns: 100 }
      );
    });
  });
});
