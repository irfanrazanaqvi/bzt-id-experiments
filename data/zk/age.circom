pragma circom 2.0.0;
include "circomlib/circuits/poseidon.circom";
include "circomlib/circuits/comparators.circom";

// Prove "holder is at least minDays old" for a date of birth that is bound to an issuer-signed
// Poseidon commitment, without revealing the date of birth.
template AgeProof() {
    signal input dob;          // private: days since 1900-01-01
    signal input salt;         // private
    signal input commitment;   // public: Poseidon(dob, salt), as stored in the credential
    signal input today;        // public: days since 1900-01-01
    signal input minDays;      // public: e.g. 18 * 365.25 = 6575

    component H = Poseidon(2);
    H.inputs[0] <== dob;
    H.inputs[1] <== salt;
    H.out === commitment;

    component ge = GreaterEqThan(32);
    ge.in[0] <== today - dob;
    ge.in[1] <== minDays;
    ge.out === 1;
}
component main { public [commitment, today, minDays] } = AgeProof();
