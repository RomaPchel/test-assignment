class ExtractionFailure(Exception):
    """Document extraction failed (OCR error, unsupported format)"""
    pass


class GateTimeout(Exception):
    """Gate execution exceeded timeout limit"""
    pass


class MalformedModelOutput(Exception):
    """Claude returned invalid or unparseable JSON"""
    pass
