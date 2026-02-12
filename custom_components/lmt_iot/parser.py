"""Message parser for LMT IoT Device uplink messages."""


def parse_uplink_message(payload: dict) -> dict | None:
    """Parse uplink message (V1 or V2 format)."""
    if payload.get("version") == "V2":
        return _parse_v2_uplink(payload)
    elif "data" in payload and "msdInfoData" in payload:
        return _parse_v1_uplink(payload)
    
    return None


def _parse_v1_uplink(payload: dict) -> dict | None:
    """Parse v1 uplink message format."""
    if not isinstance(payload["data"], list):
        return None
    
    server_identity = payload["msdInfoData"].get("mServerIdentity")
    
    for device_data in payload["data"]:
        if device_data.get("mSerial") != server_identity:
            continue
            
        parsed = {}
        
        if "mTempData" in device_data and device_data["mTempData"]:
            temp_data = device_data["mTempData"][0]["mData"]
            if temp_data:
                parsed["TEMPERATURE"] = temp_data[-1]
        
        if "mHumidData" in device_data and device_data["mHumidData"]:
            humid_data = device_data["mHumidData"][0]["mData"]
            if humid_data:
                parsed["HUMIDITY"] = humid_data[-1]
        
        if "mCoData" in device_data and device_data["mCoData"]:
            co_data = device_data["mCoData"][0]["mData"]
            if co_data:
                parsed["CO"] = co_data[-1]
        
        if "mIaqData" in device_data and device_data["mIaqData"]:
            iaq_data = device_data["mIaqData"][0]["mData"]
            if iaq_data:
                parsed["IAQ"] = iaq_data[-1]
        
        if "mSmokeStatus" in device_data:
            smoke_status = device_data["mSmokeStatus"]
            status_map = {0: "OK", 1: "WARNING", 2: "ALARM"}
            parsed["SMOKE_STATUS"] = status_map.get(smoke_status, "UNKNOWN")
        
        if "mRsrp" in device_data and device_data["mRsrp"] is not None:
            parsed["RSRP"] = device_data["mRsrp"]
        if "mRsrq" in device_data and device_data["mRsrq"] is not None:
            parsed["RSRQ"] = device_data["mRsrq"]
        if "mSinr" in device_data and device_data["mSinr"] is not None:
            parsed["SINR"] = device_data["mSinr"]
        
        return parsed if parsed else None
    
    return None


def _parse_v2_uplink(payload: dict) -> dict | None:
    """Parse v2 uplink message format."""
    measurements = payload.get("measurements", {})
    if not measurements:
        return None
    
    parsed = {}
    
    for key, values in measurements.items():
        if key == "SIGNAL_STRENGTH" and values:
            signal = values[-1]
            if len(signal) >= 4:
                try:
                    parsed["RSRP"] = int(signal[1])
                    parsed["RSRQ"] = int(signal[2])
                    parsed["SINR"] = int(signal[3])
                except (ValueError, TypeError, IndexError):
                    pass
        elif values:
            try:
                parsed[key] = float(values[-1][1])
            except (ValueError, TypeError, IndexError):
                pass
    
    return parsed if parsed else None
