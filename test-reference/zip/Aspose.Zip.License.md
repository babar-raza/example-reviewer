---
linkTitle: "Class License"
title: "Class License"
description: "Provides methods to license the component."
summary: "Provides methods to license the component."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip](/zip/)  
Assembly: Aspose.Zip.dll (25.12.0)  

Provides methods to license the component.

```csharp
public sealed class License
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[License](/zip/aspose.zip.license)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Examples

In this example, an attempt will be made to find a license file named MyLicense.lic
in the folder that contains 
<ms>
the component, in the folder that contains the calling assembly,
in the folder of the entry assembly and then in the embedded resources of the calling assembly.

```csharp
License license = new License();
license.SetLicense("MyLicense.lic");
```
```vb
Dim license As license = New license
License.SetLicense("MyLicense.lic")
```</ms><java>
the component jar file:

```csharp
License license = new License();
license.setLicense("MyLicense.lic");
```</java>

## Constructors

### <a id="Aspose_Zip_License__ctor"></a> License\(\)

Initializes a new instance of the Aspose.Zip.License class.

```csharp
public License()
```

#### Examples

In this example, an attempt will be made to find a license file named MyLicense.lic
in the folder that contains 
<ms>
the component, in the folder that contains the calling assembly,
in the folder of the entry assembly and then in the embedded resources of the calling assembly.

```csharp
License license = new License();
license.SetLicense("MyLicense.lic");
```
```vb
Dim license As license = New license
License.SetLicense("MyLicense.lic")
```</ms><java>
the component jar file:

```csharp
License license = new License();
license.setLicense("MyLicense.lic");
```</java>

## Methods

### <a id="Aspose_Zip_License_SetLicense_System_String_"></a> SetLicense\(string\)

Licenses the component.

```csharp
public void SetLicense(string licenseName)
```

#### Parameters

`licenseName` [string](https://learn.microsoft.com/dotnet/api/system.string)

Can be a full or short file name or name of an embedded resource.
            Use an empty string to switch to evaluation mode.

#### Examples

In this example, an attempt will be made to find a license file named MyLicense.lic
in the folder that contains 
<ms>
the component, in the folder that contains the calling assembly,
in the folder of the entry assembly and then in the embedded resources of the calling assembly.

```csharp
License license = new License();
license.SetLicense("MyLicense.lic");
```</ms><java>
the component jar file:

```csharp
License license = new License();
license.setLicense("MyLicense.lic");
```</java>

#### Remarks

<p>Tries to find the license in the following locations:</p>
<p>1. Explicit path.</p>
<ms>
  <p>2. The folder that contains the Aspose component assembly.</p>
  <p>3. The folder that contains the client's calling assembly.</p>
  <p>4. The folder that contains the entry (startup) assembly.</p>
  <p>5. An embedded resource in the client's calling assembly.</p>
  <p>
    <b>Note:</b>On the .NET Compact Framework, tries to find the license only in these locations:</p>
  <p>1. Explicit path.</p>
  <p>2. An embedded resource in the client's calling assembly.</p>
</ms>
<java>
  <p>2. The folder that contains the Aspose component JAR file.</p>
  <p>3. The folder that contains the client's calling JAR file.</p>
</java>

### <a id="Aspose_Zip_License_SetLicense_System_IO_Stream_"></a> SetLicense\(Stream\)

Licenses the component.

```csharp
public void SetLicense(Stream stream)
```

#### Parameters

`stream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

A stream that contains the license.

#### Examples


```csharp
License license = new License();
license.SetLicense(myStream);
```
```vb
Dim license as License = new License
license.SetLicense(myStream)


License license = new License();
license.setLicense(myStream);
```

#### Remarks

<p>Use this method to load a license from a stream.</p>
