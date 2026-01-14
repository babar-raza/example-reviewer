---
linkTitle: "Class FastLZStream"
title: "Class FastLZStream"
description: "A stream wrapper that compresses data with FastLZ. Implements decorator pattern."
summary: "A stream wrapper that compresses data with FastLZ. Implements decorator pattern."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Zip.FastLZ](/zip/aspose.zip.fastlz)  
Assembly: Aspose.Zip.dll (25.12.0)  

A stream wrapper that compresses data with FastLZ. Implements decorator pattern.

```csharp
public class FastLZStream : Stream, IDisposable, IAsyncDisposable
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[MarshalByRefObject](https://learn.microsoft.com/dotnet/api/system.marshalbyrefobject) ← 
[Stream](https://learn.microsoft.com/dotnet/api/system.io.stream) ← 
[FastLZStream](/zip/aspose.zip.fastlz.fastlzstream)

#### Implements

[IDisposable](https://learn.microsoft.com/dotnet/api/system.idisposable), 
[IAsyncDisposable](https://learn.microsoft.com/dotnet/api/system.iasyncdisposable)

#### Inherited Members

[Stream.Null](https://learn.microsoft.com/dotnet/api/system.io.stream.null), 
[Stream.CopyTo\(Stream\)](https://learn.microsoft.com/dotnet/api/system.io.stream.copyto\#system\-io\-stream\-copyto\(system\-io\-stream\)), 
[Stream.CopyTo\(Stream, int\)](https://learn.microsoft.com/dotnet/api/system.io.stream.copyto\#system\-io\-stream\-copyto\(system\-io\-stream\-system\-int32\)), 
[Stream.CopyToAsync\(Stream\)](https://learn.microsoft.com/dotnet/api/system.io.stream.copytoasync\#system\-io\-stream\-copytoasync\(system\-io\-stream\)), 
[Stream.CopyToAsync\(Stream, int\)](https://learn.microsoft.com/dotnet/api/system.io.stream.copytoasync\#system\-io\-stream\-copytoasync\(system\-io\-stream\-system\-int32\)), 
[Stream.CopyToAsync\(Stream, CancellationToken\)](https://learn.microsoft.com/dotnet/api/system.io.stream.copytoasync\#system\-io\-stream\-copytoasync\(system\-io\-stream\-system\-threading\-cancellationtoken\)), 
[Stream.CopyToAsync\(Stream, int, CancellationToken\)](https://learn.microsoft.com/dotnet/api/system.io.stream.copytoasync\#system\-io\-stream\-copytoasync\(system\-io\-stream\-system\-int32\-system\-threading\-cancellationtoken\)), 
[Stream.Dispose\(\)](https://learn.microsoft.com/dotnet/api/system.io.stream.dispose\#system\-io\-stream\-dispose), 
[Stream.Close\(\)](https://learn.microsoft.com/dotnet/api/system.io.stream.close), 
[Stream.Dispose\(bool\)](https://learn.microsoft.com/dotnet/api/system.io.stream.dispose\#system\-io\-stream\-dispose\(system\-boolean\)), 
[Stream.DisposeAsync\(\)](https://learn.microsoft.com/dotnet/api/system.io.stream.disposeasync), 
[Stream.Flush\(\)](https://learn.microsoft.com/dotnet/api/system.io.stream.flush), 
[Stream.FlushAsync\(\)](https://learn.microsoft.com/dotnet/api/system.io.stream.flushasync\#system\-io\-stream\-flushasync), 
[Stream.FlushAsync\(CancellationToken\)](https://learn.microsoft.com/dotnet/api/system.io.stream.flushasync\#system\-io\-stream\-flushasync\(system\-threading\-cancellationtoken\)), 
[Stream.CreateWaitHandle\(\)](https://learn.microsoft.com/dotnet/api/system.io.stream.createwaithandle), 
[Stream.BeginRead\(byte\[\], int, int, AsyncCallback?, object?\)](https://learn.microsoft.com/dotnet/api/system.io.stream.beginread), 
[Stream.EndRead\(IAsyncResult\)](https://learn.microsoft.com/dotnet/api/system.io.stream.endread), 
[Stream.ReadAsync\(byte\[\], int, int\)](https://learn.microsoft.com/dotnet/api/system.io.stream.readasync\#system\-io\-stream\-readasync\(system\-byte\(\)\-system\-int32\-system\-int32\)), 
[Stream.ReadAsync\(byte\[\], int, int, CancellationToken\)](https://learn.microsoft.com/dotnet/api/system.io.stream.readasync\#system\-io\-stream\-readasync\(system\-byte\(\)\-system\-int32\-system\-int32\-system\-threading\-cancellationtoken\)), 
[Stream.ReadAsync\(Memory<byte\>, CancellationToken\)](https://learn.microsoft.com/dotnet/api/system.io.stream.readasync\#system\-io\-stream\-readasync\(system\-memory\(\(system\-byte\)\)\-system\-threading\-cancellationtoken\)), 
[Stream.ReadExactlyAsync\(Memory<byte\>, CancellationToken\)](https://learn.microsoft.com/dotnet/api/system.io.stream.readexactlyasync\#system\-io\-stream\-readexactlyasync\(system\-memory\(\(system\-byte\)\)\-system\-threading\-cancellationtoken\)), 
[Stream.ReadExactlyAsync\(byte\[\], int, int, CancellationToken\)](https://learn.microsoft.com/dotnet/api/system.io.stream.readexactlyasync\#system\-io\-stream\-readexactlyasync\(system\-byte\(\)\-system\-int32\-system\-int32\-system\-threading\-cancellationtoken\)), 
[Stream.ReadAtLeastAsync\(Memory<byte\>, int, bool, CancellationToken\)](https://learn.microsoft.com/dotnet/api/system.io.stream.readatleastasync), 
[Stream.BeginWrite\(byte\[\], int, int, AsyncCallback?, object?\)](https://learn.microsoft.com/dotnet/api/system.io.stream.beginwrite), 
[Stream.EndWrite\(IAsyncResult\)](https://learn.microsoft.com/dotnet/api/system.io.stream.endwrite), 
[Stream.WriteAsync\(byte\[\], int, int\)](https://learn.microsoft.com/dotnet/api/system.io.stream.writeasync\#system\-io\-stream\-writeasync\(system\-byte\(\)\-system\-int32\-system\-int32\)), 
[Stream.WriteAsync\(byte\[\], int, int, CancellationToken\)](https://learn.microsoft.com/dotnet/api/system.io.stream.writeasync\#system\-io\-stream\-writeasync\(system\-byte\(\)\-system\-int32\-system\-int32\-system\-threading\-cancellationtoken\)), 
[Stream.WriteAsync\(ReadOnlyMemory<byte\>, CancellationToken\)](https://learn.microsoft.com/dotnet/api/system.io.stream.writeasync\#system\-io\-stream\-writeasync\(system\-readonlymemory\(\(system\-byte\)\)\-system\-threading\-cancellationtoken\)), 
[Stream.Seek\(long, SeekOrigin\)](https://learn.microsoft.com/dotnet/api/system.io.stream.seek), 
[Stream.SetLength\(long\)](https://learn.microsoft.com/dotnet/api/system.io.stream.setlength), 
[Stream.Read\(byte\[\], int, int\)](https://learn.microsoft.com/dotnet/api/system.io.stream.read\#system\-io\-stream\-read\(system\-byte\(\)\-system\-int32\-system\-int32\)), 
[Stream.Read\(Span<byte\>\)](https://learn.microsoft.com/dotnet/api/system.io.stream.read\#system\-io\-stream\-read\(system\-span\(\(system\-byte\)\)\)), 
[Stream.ReadByte\(\)](https://learn.microsoft.com/dotnet/api/system.io.stream.readbyte), 
[Stream.ReadExactly\(Span<byte\>\)](https://learn.microsoft.com/dotnet/api/system.io.stream.readexactly\#system\-io\-stream\-readexactly\(system\-span\(\(system\-byte\)\)\)), 
[Stream.ReadExactly\(byte\[\], int, int\)](https://learn.microsoft.com/dotnet/api/system.io.stream.readexactly\#system\-io\-stream\-readexactly\(system\-byte\(\)\-system\-int32\-system\-int32\)), 
[Stream.ReadAtLeast\(Span<byte\>, int, bool\)](https://learn.microsoft.com/dotnet/api/system.io.stream.readatleast), 
[Stream.Write\(byte\[\], int, int\)](https://learn.microsoft.com/dotnet/api/system.io.stream.write\#system\-io\-stream\-write\(system\-byte\(\)\-system\-int32\-system\-int32\)), 
[Stream.Write\(ReadOnlySpan<byte\>\)](https://learn.microsoft.com/dotnet/api/system.io.stream.write\#system\-io\-stream\-write\(system\-readonlyspan\(\(system\-byte\)\)\)), 
[Stream.WriteByte\(byte\)](https://learn.microsoft.com/dotnet/api/system.io.stream.writebyte), 
[Stream.Synchronized\(Stream\)](https://learn.microsoft.com/dotnet/api/system.io.stream.synchronized), 
[Stream.ObjectInvariant\(\)](https://learn.microsoft.com/dotnet/api/system.io.stream.objectinvariant), 
[Stream.ValidateBufferArguments\(byte\[\], int, int\)](https://learn.microsoft.com/dotnet/api/system.io.stream.validatebufferarguments), 
[Stream.ValidateCopyToArguments\(Stream, int\)](https://learn.microsoft.com/dotnet/api/system.io.stream.validatecopytoarguments), 
[Stream.CanRead](https://learn.microsoft.com/dotnet/api/system.io.stream.canread), 
[Stream.CanWrite](https://learn.microsoft.com/dotnet/api/system.io.stream.canwrite), 
[Stream.CanSeek](https://learn.microsoft.com/dotnet/api/system.io.stream.canseek), 
[Stream.CanTimeout](https://learn.microsoft.com/dotnet/api/system.io.stream.cantimeout), 
[Stream.Length](https://learn.microsoft.com/dotnet/api/system.io.stream.length), 
[Stream.Position](https://learn.microsoft.com/dotnet/api/system.io.stream.position), 
[Stream.ReadTimeout](https://learn.microsoft.com/dotnet/api/system.io.stream.readtimeout), 
[Stream.WriteTimeout](https://learn.microsoft.com/dotnet/api/system.io.stream.writetimeout), 
[MarshalByRefObject.GetLifetimeService\(\)](https://learn.microsoft.com/dotnet/api/system.marshalbyrefobject.getlifetimeservice), 
[MarshalByRefObject.InitializeLifetimeService\(\)](https://learn.microsoft.com/dotnet/api/system.marshalbyrefobject.initializelifetimeservice), 
[MarshalByRefObject.MemberwiseClone\(bool\)](https://learn.microsoft.com/dotnet/api/system.marshalbyrefobject.memberwiseclone), 
[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_Zip_FastLZ_FastLZStream__ctor_System_IO_Stream_System_Int32_"></a> FastLZStream\(Stream, int\)

Initializes a new instance of the Aspose.Zip.FastLZ.FastLZStream class prepared for compression.

```csharp
public FastLZStream(Stream stream, int compressionLevel)
```

#### Parameters

`stream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The stream for saving compressed data.

`compressionLevel` [int](https://learn.microsoft.com/dotnet/api/system.int32)

Use 1 for faster compression, use 2 for a better compression ratio.

#### Exceptions

 [ArgumentNullException](https://learn.microsoft.com/dotnet/api/system.argumentnullexception)

<code class="paramref">stream</code> is null.

 [ArgumentException](https://learn.microsoft.com/dotnet/api/system.argumentexception)

<code class="paramref">stream</code> does not support writing.

 [ArgumentOutOfRangeException](https://learn.microsoft.com/dotnet/api/system.argumentoutofrangeexception)

<code class="paramref">compressionLevel</code> is more than 2 or less than 1.

## Properties

### <a id="Aspose_Zip_FastLZ_FastLZStream_CanRead"></a> CanRead

Gets a value indicating whether the current stream supports reading.

```csharp
public override bool CanRead { get; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

### <a id="Aspose_Zip_FastLZ_FastLZStream_CanSeek"></a> CanSeek

Gets a value indicating whether the current stream supports seeking.

```csharp
public override bool CanSeek { get; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

### <a id="Aspose_Zip_FastLZ_FastLZStream_CanWrite"></a> CanWrite

Gets a value indicating whether the current stream supports writing.

```csharp
public override bool CanWrite { get; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

### <a id="Aspose_Zip_FastLZ_FastLZStream_Length"></a> Length

Gets the length in bytes of the stream.

```csharp
public override long Length { get; }
```

#### Property Value

 [long](https://learn.microsoft.com/dotnet/api/system.int64)

### <a id="Aspose_Zip_FastLZ_FastLZStream_Position"></a> Position

Gets or sets the position within the current stream.

```csharp
public override long Position { get; set; }
```

#### Property Value

 [long](https://learn.microsoft.com/dotnet/api/system.int64)

## Methods

### <a id="Aspose_Zip_FastLZ_FastLZStream_Close"></a> Close\(\)

Closes the current stream and releases any resources (such as sockets and file handles) associated with the current stream.

```csharp
public override void Close()
```

### <a id="Aspose_Zip_FastLZ_FastLZStream_Flush"></a> Flush\(\)

Clears all buffers for this stream and causes any buffered data to be written to the underlying device.

```csharp
public override void Flush()
```

### <a id="Aspose_Zip_FastLZ_FastLZStream_Read_System_Byte___System_Int32_System_Int32_"></a> Read\(byte\[\], int, int\)

Reads a sequence of bytes from the stream and advances the position within the stream by the number of bytes read. Not supported.

```csharp
public override int Read(byte[] buffer, int offset, int count)
```

#### Parameters

`buffer` [byte](https://learn.microsoft.com/dotnet/api/system.byte)\[\]

An array of bytes. When this method returns, the buffer contains the specified byte array with the values between offset and (offset + count - 1) replaced by the bytes read from the current source.

`offset` [int](https://learn.microsoft.com/dotnet/api/system.int32)

The zero-based byte offset in buffer at which to begin storing the data read from the current stream.

`count` [int](https://learn.microsoft.com/dotnet/api/system.int32)

The maximum number of bytes to be read from the current stream.

#### Returns

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

The total number of bytes read into the buffer. This can be less than the number of bytes requested if that many bytes are not currently available, or zero (0) if the end of the stream has been reached.

### <a id="Aspose_Zip_FastLZ_FastLZStream_Seek_System_Int64_System_IO_SeekOrigin_"></a> Seek\(long, SeekOrigin\)

Sets the position within the current stream.

```csharp
public override long Seek(long offset, SeekOrigin origin)
```

#### Parameters

`offset` [long](https://learn.microsoft.com/dotnet/api/system.int64)

A byte offset relative to the origin parameter.

`origin` [SeekOrigin](https://learn.microsoft.com/dotnet/api/system.io.seekorigin)

A value of type SeekOrigin indicating the reference point used to obtain the new position.

#### Returns

 [long](https://learn.microsoft.com/dotnet/api/system.int64)

The new position within the current stream.

### <a id="Aspose_Zip_FastLZ_FastLZStream_SetLength_System_Int64_"></a> SetLength\(long\)

Sets the length of the current stream.

```csharp
public override void SetLength(long value)
```

#### Parameters

`value` [long](https://learn.microsoft.com/dotnet/api/system.int64)

The desired length of the current stream in bytes.

### <a id="Aspose_Zip_FastLZ_FastLZStream_Write_System_Byte___System_Int32_System_Int32_"></a> Write\(byte\[\], int, int\)

Writes a sequence of bytes to the compressing stream and advances the current position within this stream by the number of bytes written.

```csharp
public override void Write(byte[] buffer, int offset, int count)
```

#### Parameters

`buffer` [byte](https://learn.microsoft.com/dotnet/api/system.byte)\[\]

An array of bytes. This method copies count bytes from buffer to the current stream.

`offset` [int](https://learn.microsoft.com/dotnet/api/system.int32)

The zero-based byte offset in buffer at which to begin copying bytes to the current stream.

`count` [int](https://learn.microsoft.com/dotnet/api/system.int32)

The number of bytes to be written to the current stream.
