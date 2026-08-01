Implementation Outline

1.  Product Contract
    - Define supported behavior, preservation guarantees, safety rules, and explicit limitations.

2.  Google-Native Document Model
    - Losslessly represent the physical Google document structure relevant to reading and mutation.

3.  Google API Ingress
    - Convert a Google Docs response into the native model without semantic normalization or structural information loss.

4.  User-Facing Document View
    - Project the native model into a stable, editable representation and map that representation back to native nodes.

5.  Edit Intent
    - Express the user’s requested change independently of Google API requests and indices.

6.  Native Document Editor
    - Apply edit intent directly to the Google-native model while retaining untouched nodes and provider state.

7.  Google Mutation Generation
    - Derive the minimal Google API operations needed to move from the current native document to the edited native document.

8.  Mutation Execution
    - Submit revision-controlled operations safely, classify outcomes, and avoid unsafe retries.

9.  Result Verification
    - Read the resulting document and confirm that the requested user-visible change occurred while required untouched state survived.

10. Capability and Preservation Boundaries
    - Reject operations that cannot safely preserve unsupported or externally anchored provider state.

11. Command Interface
    - Connect read, edit, and write commands to the same small set of deep document operations.

12. Testing Strategy
    - Test native model fidelity, general editing laws, exact API behavior, preservation, and complete user journeys.

13. Migration
    - Build the new path independently, prove it against current behavior, switch over, and delete the old compiler architecture.

14. Complexity and Deletion Acceptance
    - Enforce the production-module, class, test-matrix, and line-deletion requirements recorded in the redesign specification.
