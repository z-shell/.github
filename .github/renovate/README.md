# Renovate preset


```json
{
  "extends": [
    ":dependencyDashboard",
    ":semanticPrefixFixDepsChoreOthers",
    ":ignoreModulesAndTests",
    ":autodetectPinVersions",
    ":prHourlyLimit2",
    ":prConcurrentLimit10",
    "group:monorepos",
    "group:recommended",
    "workarounds:all"
  ]
}
```

```json
{
  "groupName": "all dependencies",
  "separateMajorMinor": false,
  "groupSlug": "all",
  "packageRules": [
    {
      "matchPackagePatterns": [
        "*"
      ],
      "groupName": "all dependencies",
      "groupSlug": "all"
    }
  ],
  "lockFileMaintenance": {
    "enabled": false
  }
}
```
