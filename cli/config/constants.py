"""
ODRL & OAC Constants, Contexts, and DUODRL Vocabulary Mappings.
Based on:
- W3C ODRL 2.2: https://www.w3.org/TR/odrl-vocab/
- OAC Profile: https://w3id.org/oac/
- DUODRL Profile: https://w3id.org/duodrl#
"""

ODRL_CONTEXT = "http://www.w3.org/ns/odrl.jsonld"
OAC_CONTEXT = "https://w3id.org/oac/context.json"
DUODRL_CONTEXT = "https://w3id.org/duodrl#"
ODRL_PREFIX = "odrl:"
DUODRL_PREFIX = "duodrl:"

# DUODRL Mapping & Profile Terms (https://w3id.org/duodrl#)
DUODRL_MAPPINGS = {
    "DUO_0000042": {
        "code": "obo:DUO_0000042",
        "name": "GRU",
        "label": "General Research Use",
        "type": "Permission",
        "action": "odrl:use",
        "target": "duodrl:TemplateDataset",
        "operand": "oac:Purpose",
        "operator": "odrl:isA",
        "value": "duodrl:GRU",
        "description": "Allowed for general research use for any research purpose.",
    },
    "DUO_0000024": {
        "code": "obo:DUO_0000024",
        "name": "MOR",
        "label": "Publication Moratorium",
        "type": "Prohibition",
        "action": "odrl:distribute",
        "target": "duodrl:TemplateDataset",
        "output": "duodrl:ResultsOfStudies",
        "operand": "odrl:dateTime",
        "operator": "odrl:lt",
        "value": "duodrl:TemplateStudyResultsPublicationDate",
        "description": "Requestor agrees not to publish results of studies until specific date.",
    },
    "DUO_0000004": {
        "code": "obo:DUO_0000004",
        "name": "NPOA",
        "label": "Non-Profit Use Only",
        "type": "Prohibition",
        "action": "odrl:commercialize",
        "target": "duodrl:TemplateDataset",
        "operand": "odrl:recipient",
        "operator": "odrl:isA",
        "value": "duodrl:NonProfitOrganisation",
        "description": "Commercial use or use by for-profit entities is prohibited.",
    },
    "DUO_0000006": {
        "code": "obo:DUO_0000006",
        "name": "GS",
        "label": "Geographical Specificity",
        "type": "Permission",
        "action": "odrl:use",
        "target": "duodrl:TemplateDataset",
        "operand": "odrl:spatial",
        "operator": "odrl:isPartOf",
        "value": "duodrl:TemplateGeographicLocation",
        "description": "Use is limited to a specific geographic region or jurisdiction.",
    },
    "DUO_0000007": {
        "code": "obo:DUO_0000007",
        "name": "TS",
        "label": "Time Specificity",
        "type": "Permission",
        "action": "odrl:use",
        "target": "duodrl:TemplateDataset",
        "operand": "odrl:timeInterval",
        "operator": "odrl:lteq",
        "value": "duodrl:TemplateTimePeriod",
        "description": "Use is limited to a specific time period or expiry window.",
    },
    "DUO_0000018": {
        "code": "obo:DUO_0000018",
        "name": "RS",
        "label": "Research Specificity",
        "type": "Permission",
        "action": "odrl:use",
        "target": "duodrl:TemplateDataset",
        "operand": "oac:Purpose",
        "operator": "odrl:isA",
        "value": "duodrl:TemplateSpecificProject",
        "description": "Use is limited to the specified research project.",
    },
    "DUO_0000026": {
        "code": "obo:DUO_0000026",
        "name": "DS",
        "label": "Disease Specificity",
        "type": "Permission",
        "action": "odrl:use",
        "target": "duodrl:TemplateDataset",
        "operand": "oac:Purpose",
        "operator": "odrl:isA",
        "value": "duodrl:TemplateDiseaseOrCondition",
        "description": "Use is restricted to a specific disease, syndrome, or medical condition.",
    },
    "DUO_0000043": {
        "code": "obo:DUO_0000043",
        "name": "HMB",
        "label": "Health/Medical/Biomedical Research",
        "type": "Permission",
        "action": "odrl:use",
        "target": "duodrl:TemplateDataset",
        "operand": "oac:Purpose",
        "operator": "odrl:isA",
        "value": "duodrl:HealthMedicalBiomedicalResearch",
        "description": "Allowed for health, medical, or biomedical research purpose.",
    },
    "DUO_0000045": {
        "code": "obo:DUO_0000045",
        "name": "COL",
        "label": "Collaboration Required",
        "type": "Duty",
        "action": "duodrl:collaborate",
        "target": "duodrl:TemplateDataset",
        "operand": "odrl:recipient",
        "operator": "odrl:isA",
        "value": "duodrl:Collaborator",
        "description": "The user must collaborate with the primary study investigators.",
    },
    "DUO_0000046": {
        "code": "obo:DUO_0000046",
        "name": "IRB",
        "label": "Ethics Approval Required",
        "type": "Duty",
        "action": "duodrl:obtainEthicsApproval",
        "target": "duodrl:TemplateDataset",
        "operand": "odrl:recipient",
        "operator": "odrl:isA",
        "value": "duodrl:EthicalApprovalGranted",
        "description": "The user must provide proof of ethical / IRB approval prior to access.",
    },
}

