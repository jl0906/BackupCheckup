# Changelog

## 3.0.3

### Security

- Encrypted all integration-to-runner traffic with persistent, certificate-pinned
  TLS and exact SHA-256 runner-certificate verification.
- Moved temporary runtime data from the shared temporary directory to a private
  runtime directory and restricted persistent credentials to the app user.
- Documented the required root privileges and internal Supervisor proxy as
  reviewed exceptions for the isolated network-namespace setup.
- Completed the documented SonarCloud security remediations.

### Fixed

- Recovered existing runner registrations directly from Supervisor discovery
  state and continued checking when the runner starts after Home Assistant.
- Accepted both structured and legacy Home Assistant discovery payloads.
- Retried runner registration while Home Assistant or the Supervisor is still
  starting instead of giving up after the first failed attempt.
- Classified `hassio.local` as local storage and every `hassio.<mount>` backup
  target as Home Assistant OS network storage, independent of its display name.
- Prevented correctly configured local and network copies from causing an
  unclassified-storage deduction, incorrect recommendation, or score reduction.
- Fixed inconsistent version identifiers that prevented the updated frontend
  element from registering.
- Fixed the Runtime Runner image build by keeping comments out of Docker's
  `USER` instruction.

### Changed

- Reduced frontend and coordinator cognitive complexity and removed the remaining
  open SonarCloud code-smell patterns.
- Consolidated repeated recovery-assessment serialization.
- Excluded packed frontend localization tables from duplication analysis while
  retaining all other Sonar security and code-quality checks for the panel.
