# Current-version upgrade execution evidence

These reports were produced by genuine installed Semantica0.7.0+ontologyworkspace.4 through the same platform Adapter/shared technical inputs in `.venv` and a newly created independent project-local Python3.12 environment. Fifteen calls per environment: seven success cases, seven deliberately invalid source hashes, one invalid recursive-rule case. SDK/contract versions and input SHA256 are recorded, not inferred from Fake tests.

The original comparison failed solely on anonymous SHACL Shape labels, exit1; that original result is preserved. A new real-input regression demonstrated the actual native random label field, then the comparer normalized only recognized anonymous labels while preserving named Shape IDs, constraint values, severity and input binding. The corrected comparison passed with empty schema/capability/semantic/error differences, exit0. It does not mean the earlier failure passed.

The gate execution record separately shows actual contract tests, baseline report production, fresh offline locked install and candidate report production all exit0 with distinct environments and compatible=true. Full repository regression after fixes:292passed+14subtests153.16s exit0. Offline install98resolved/96installed; official small spaCy model retained from approved lock/cache, no new model or latest SDK substitution.

No future SDK version was provided or executed. Controlled destructive report mutations in unit tests are comparer tests, not native-version evidence. This archive is execution/reproducibility evidence only: independent security review pending, release_approved=false, no product/P1–P8/Linux deployment claim. Original0.7.0/.3 and earlier.4 evidence remains unchanged.
