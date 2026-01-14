---
linkTitle: "Class SevenZipCipher"
title: "Class SevenZipCipher"
description: "Base class for AES cipher used for 7-zip encryption."
summary: "Base class for AES cipher used for 7-zip encryption."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.Crypto](/zip/aspose.zip.crypto)  
Assembly: Aspose.Zip.dll (25.12.0)  

Base class for AES cipher used for 7-zip encryption.

```csharp
public abstract class SevenZipCipher : ICryptoTransform, IDisposable
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[SevenZipCipher](/zip/aspose.zip.crypto.sevenzipcipher)

#### Implements

[ICryptoTransform](https://learn.microsoft.com/dotnet/api/system.security.cryptography.icryptotransform), 
[IDisposable](https://learn.microsoft.com/dotnet/api/system.idisposable)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_Crypto_SevenZipCipher__ctor"></a> SevenZipCipher\(\)

Initializes a new instance of the Aspose.Zip.Crypto.SevenZipCipher.

```csharp
protected SevenZipCipher()
```

#### Exceptions

 [CryptographicException](https://learn.microsoft.com/dotnet/api/system.security.cryptography.cryptographicexception)

The Aspose.Zip.Crypto.SevenZipCipher.NumberOfCyclesPower is too big.

## Properties

### <a id="Aspose_Zip_Crypto_SevenZipCipher_CanReuseTransform"></a> CanReuseTransform

Gets a value indicating whether the current transform can be reused.

```csharp
public abstract bool CanReuseTransform { get; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

### <a id="Aspose_Zip_Crypto_SevenZipCipher_CanTransformMultipleBlocks"></a> CanTransformMultipleBlocks

Gets a value indicating whether multiple blocks can be transformed.

```csharp
public abstract bool CanTransformMultipleBlocks { get; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

### <a id="Aspose_Zip_Crypto_SevenZipCipher_InputBlockSize"></a> InputBlockSize

Gets the input block size.

```csharp
public abstract int InputBlockSize { get; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

### <a id="Aspose_Zip_Crypto_SevenZipCipher_LastBlockUnderflowSize"></a> LastBlockUnderflowSize

Gets the number of lacking bytes within the last block.

```csharp
protected abstract int LastBlockUnderflowSize { get; set; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

### <a id="Aspose_Zip_Crypto_SevenZipCipher_NumberOfCyclesPower"></a> NumberOfCyclesPower

Gets binary logarithm of the number of cycles used for AES key calculation.

```csharp
protected virtual byte NumberOfCyclesPower { get; set; }
```

#### Property Value

 [byte](https://learn.microsoft.com/dotnet/api/system.byte)

#### Remarks

Default value is 19. Must not exceed 24.

### <a id="Aspose_Zip_Crypto_SevenZipCipher_OutputBlockSize"></a> OutputBlockSize

Gets the output block size.

```csharp
public abstract int OutputBlockSize { get; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

### <a id="Aspose_Zip_Crypto_SevenZipCipher_Salt"></a> Salt

Gets the salt used for key initialization of AES algorithm.

```csharp
protected abstract byte[] Salt { get; }
```

#### Property Value

 [byte](https://learn.microsoft.com/dotnet/api/system.byte)\[\]

### <a id="Aspose_Zip_Crypto_SevenZipCipher_Seed"></a> Seed

Gets the seed used to compose initialization vector of AES algorithm.

```csharp
protected abstract byte[] Seed { get; }
```

#### Property Value

 [byte](https://learn.microsoft.com/dotnet/api/system.byte)\[\]

## Methods

### <a id="Aspose_Zip_Crypto_SevenZipCipher_Dispose"></a> Dispose\(\)

Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources.

```csharp
public abstract void Dispose()
```

### <a id="Aspose_Zip_Crypto_SevenZipCipher_TransformBlock_System_Byte___System_Int32_System_Int32_System_Byte___System_Int32_"></a> TransformBlock\(byte\[\], int, int, byte\[\], int\)

Transforms the specified region of the input byte array and copies the resulting transform to the specified region of the output byte array.

```csharp
public abstract int TransformBlock(byte[] inputBuffer, int inputOffset, int inputCount, byte[] outputBuffer, int outputOffset)
```

#### Parameters

`inputBuffer` [byte](https://learn.microsoft.com/dotnet/api/system.byte)\[\]

The input for which to compute the transform.

`inputOffset` [int](https://learn.microsoft.com/dotnet/api/system.int32)

The offset into the input byte array from which to begin using data.

`inputCount` [int](https://learn.microsoft.com/dotnet/api/system.int32)

The number of bytes in the input byte array to use as data.

`outputBuffer` [byte](https://learn.microsoft.com/dotnet/api/system.byte)\[\]

The output to which to write the transform.

`outputOffset` [int](https://learn.microsoft.com/dotnet/api/system.int32)

The offset into the output byte array from which to begin writing data.

#### Returns

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

### <a id="Aspose_Zip_Crypto_SevenZipCipher_TransformFinalBlock_System_Byte___System_Int32_System_Int32_"></a> TransformFinalBlock\(byte\[\], int, int\)

Transforms the specified region of the specified byte array.

```csharp
public abstract byte[] TransformFinalBlock(byte[] inputBuffer, int inputOffset, int inputCount)
```

#### Parameters

`inputBuffer` [byte](https://learn.microsoft.com/dotnet/api/system.byte)\[\]

The input for which to compute the transform.

`inputOffset` [int](https://learn.microsoft.com/dotnet/api/system.int32)

The offset into the input byte array from which to begin using data.

`inputCount` [int](https://learn.microsoft.com/dotnet/api/system.int32)

The number of bytes in the input byte array to use as data.

#### Returns

 [byte](https://learn.microsoft.com/dotnet/api/system.byte)\[\]

The computed transform.
