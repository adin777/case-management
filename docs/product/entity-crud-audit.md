# Entity lifecycle audit

This matrix records the current administrative lifecycle surface. “Deactivate” is preferred for referenced business configuration; physical deletion must be rejected when references exist.

| Entity | Create | Edit | Activate | Delete | Usage check |
|---|---:|---:|---:|---:|---:|
| User | Yes | Yes | Yes | No | N/A — deactivate |
| User group | Yes | Yes | Yes | No — deactivate | Membership removal only |
| Access assignment | Yes | Yes/bulk | N/A | Replace with none | Audited |
| Environment | Yes | Yes | Yes | No | N/A — deactivate |
| Request type | Yes | Yes | Yes | No | N/A — deactivate |
| User field and values | Yes | Yes | Yes | No — deactivate | References preserved |
| Case field and values | Yes | Yes | Yes | No — deactivate | References preserved |
| Priority and sub-priority | Yes | Yes | Yes | No — deactivate | References preserved |
| Workflow, status, transition | Yes | Yes | Yes | No — deactivate | References preserved |
| Automation rule, condition, action | Yes | Yes | Yes | No — deactivate | References preserved |
| SLA policy | Yes | Yes | Yes | No — deactivate | References preserved |
| Approval flow and step | Yes | Yes | Yes | No — deactivate | References preserved |

Physical deletion of cases, comments, audit events, approval history, and notification history is outside the administrative UI. Referenced configuration remains available for historical rendering after deactivation.
