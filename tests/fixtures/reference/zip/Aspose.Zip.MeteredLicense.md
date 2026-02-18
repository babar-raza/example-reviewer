---
linkTitle: "Class MeteredLicense"
title: "Class MeteredLicense"
description: "Provides methods to set metered key."
summary: "Provides methods to set metered key."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip](/zip/)  
Assembly: Aspose.Zip.dll (25.12.0)  

Provides methods to set metered key.

```csharp
public class MeteredLicense
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[MeteredLicense](/zip/aspose.zip.meteredlicense)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Examples

In this example, an attempt will be made to set metered public and private key
<ms>
    
```csharp
Metered metered = new Metered();
    metered.SetMeteredKey("PublicKey", "PrivateKey");
```
```vb
Dim metered As Metered = New Metered
    metered.SetMeteredKey("PublicKey", "PrivateKey")
```</ms><java>
the component jar file:

```csharp
Metered metered = new Metered();
metered.setMeteredKey("PublicKey", "PrivateKey");
```</java>

## Constructors

### <a id="Aspose_Zip_MeteredLicense__ctor"></a> MeteredLicense\(\)

```csharp
public MeteredLicense()
```

## Methods

### <a id="Aspose_Zip_MeteredLicense_GetConsumptionCredit"></a> GetConsumptionCredit\(\)

Gets consumption credit.

```csharp
public static decimal GetConsumptionCredit()
```

#### Returns

 [decimal](https://learn.microsoft.com/dotnet/api/system.decimal)

Returns the number of consumed credit points.

### <a id="Aspose_Zip_MeteredLicense_GetConsumptionQuantity"></a> GetConsumptionQuantity\(\)

Gets consumption file size.

```csharp
public static decimal GetConsumptionQuantity()
```

#### Returns

 [decimal](https://learn.microsoft.com/dotnet/api/system.decimal)

Returns the number of consumed bytes.

### <a id="Aspose_Zip_MeteredLicense_ResetMeteredKey"></a> ResetMeteredKey\(\)

Removes previously setup license.

```csharp
public void ResetMeteredKey()
```

### <a id="Aspose_Zip_MeteredLicense_SetMeteredKey_System_String_System_String_"></a> SetMeteredKey\(string, string\)

Sets metered public and private keys.

```csharp
public void SetMeteredKey(string publicKey, string privateKey)
```

#### Parameters

`publicKey` [string](https://learn.microsoft.com/dotnet/api/system.string)

The public key.

`privateKey` [string](https://learn.microsoft.com/dotnet/api/system.string)

The private key.

#### Remarks

If you purchase metered license, this API should be called on application startup, normally, this is enough.
However, if metered fails to upload consumption data during 24 hours period, the license will be set to evaluation status. To avoid such case, you should regularly check the license status If it is evaluation status, call this API again.
