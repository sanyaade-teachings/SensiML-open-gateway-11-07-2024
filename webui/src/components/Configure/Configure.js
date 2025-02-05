import { Grid, Typography, Divider } from "@material-ui/core";
import Button from "@material-ui/core/Button";
import Card from "@material-ui/core/Card";
import CardContent from "@material-ui/core/CardContent";
import FormControl from "@material-ui/core/FormControl";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import FormLabel from "@material-ui/core/FormLabel";
import Radio from "@material-ui/core/Radio";
import RadioGroup from "@material-ui/core/RadioGroup";
import { makeStyles } from "@material-ui/core/styles";
import TextField from "@material-ui/core/TextField";
import axios from "axios";
import React, { useEffect } from "react";
import { Status } from "../Status";
import Scan from "./Scan";
import { WebCamera } from "../WebCamera";

const useStyles = makeStyles((theme) => ({
  root: {
    display: "flex",
  },
  formControl: {
    margin: theme.spacing(3),
    minWidth: 600,
  },
  divWrapper: {
    margin: theme.spacing(3),
    padding: theme.spacing(2, 2, 2, 2),
    maxWidth: 700,
    minWidth: 600,
  },
  button: {
    margin: theme.spacing(1, 1, 0, 0),
  },
  section1: {
    margin: theme.spacing(2, 0, 1, 0),
  },
}));

const Configure = (props) => {
  const classes = useStyles();
  const [source, setSource] = React.useState(
    props.streamingSource ? props.streamingSource : "SERIAL"
  );

  const [mode, setMode] = React.useState(
    props.streamingMode === "recognition" ? "RECOGNITION" : "DATA_CAPTURE"
  );

  const [sample_rate, setSampleRate] = React.useState(props.streamingSampleRate);

  const [deviceID, setDeviceID] = React.useState(props.deviceID);
  const [error, setError] = React.useState(false);

  const [helperText, setHelperText] = React.useState("");

  const [configuring, setIsConfiguring] = React.useState(false);

  const handleSourceChange = (event) => {
    console.log("handle radio");
    setSource(event.target.value);
  };

  const handleDeviceBaudRate = (event) => {
    console.log("handle radio");
    props.setBaudRate(event.target.value);
  };

  const handleModeChange = (event) => {
    console.log("handle mode");
    setMode(event.target.value);
  };

  const handleSampleRate = (event) => {
    console.log("handle sample rate");
    setSampleRate(event.target.value);
  };

  const handleDeviceIDChange = (event) => {
    console.log("handle device id");
    setDeviceID(event.target.value);
    setHelperText(" ");
    setError(false);
  };

  const handleRowSelection = (event) => {
    console.log(event.row.device_id);
    setDeviceID(event.row.device_id);
  };

  const handleSubmit = (event) => {
    setIsConfiguring(true);
    event.preventDefault();
    if (deviceID === "") {
      setHelperText("Must Set DeviceID");
      setIsConfiguring(false);
      return;
    }
    console.log(source);
    console.log(deviceID);
    let data = {
      device_id: deviceID,
      source: source.toLowerCase(),
      mode: mode,
    };
    if (source === "SERIAL") {
      data.baud_rate = props.baudRate;
    }
    if (source === "MICROPHONE") {
      data.sample_rate = sample_rate;
    }
    axios
      .post(`${process.env.REACT_APP_API_URL}config`, data)
      .then((response) => {
        mapdata(response.data);
        if (response.data.streaming === false) {
          setHelperText(
            "Error starting device, check the logs in the terminal for details for additional details"
          );
        } else {
          setHelperText("Device Connected");
        }
        setIsConfiguring(false);
      })
      .catch(function (error) {
        setIsConfiguring(false);
        if (error.response) {
          setHelperText(error.response.data.detail.join(", "));
          console.log(error.response.data);
          console.log(error.response.status);
          console.log(error.response.headers);
        } else if (error.request) {
          // The request was made but no response was received
          console.log(error.request);
        } else {
          // Something happened in setting up the request that triggered an Error
          console.log("Error", error.detail);
          setHelperText(error.response.data.detail.join(", "));
        }
      });
  };

  const handleDisconnectRequest = (event) => {
    axios.get(`${process.env.REACT_APP_API_URL}disconnect`).then((res) => {
      console.log(res.data);
      mapdata(res.data);
      if (res.data.streaming === false) {
        setHelperText("");
      }
    });
  };

  function mapdata(data) {
    if (data.mode) {
      props.setStreamingMode(data.mode);
    }
    if (data.protocol) {
      props.setStreamingProtocol(data.protocol);
    }
    if (data.sample_rate) {
      props.setStreamingSampleRate(data.sample_rate);
    }
    props.setIsConnected(data.streaming);
    props.setColumns(Object.keys(data.column_location).sort());
    props.setStreamingSource(data.source);
    props.setDeviceID(data.device_id);
    props.setIsCameraConnected(data.camera_on);
    props.setBaudRate(data.baud_rate);
    data.column_location =
      "column_location" in data
        ? Object.keys(data.column_location).sort().join(", ")
        : [];

    props.setConfig(data);
  }

  useEffect(() => {
    setDeviceID(props.deviceID);
    setSource(props.streamingSource);
    setMode(props.streamingMode.toUpperCase());
    setSampleRate(props.streamingSampleRate);
  }, [props.deviceID, props.streamingSource, props.streamingMode, props.streamingProtocol, props.streamingSampleRate]);

  return (
    <Grid container columns>
      <Grid item>
        <Card className={classes.divWrapper}>
          <CardContent>
            <div className={classes.section1}>
              <Typography component="h3" variant="h3" color="secondary">
                Device Source
              </Typography>
            </div>

            <div className={classes.section1}>
              <Divider variant="middle" />
            </div>
            {props.isConnected ? (
              <React.Fragment>
                <Status
                  setStreamingMode={props.setStreamingMode}
                  setStreamingSampleRate={props.setStreamingSampleRate}
                  setColumns={props.setColumns}
                  setStreamingSource={props.setStreamingSource}
                  setDeviceID={props.setDeviceID}
                  setIsConnected={props.setIsConnected}
                  isConnected={props.isConnected}
                  setIsCameraConnected={props.setIsCameraConnected}
                  isCameraConnected={props.isCameraConnected}
                  config={props.config}
                />
                <Button
                  type="submit"
                  variant="contained"
                  color="primary"
                  disabled={configuring}
                  fullWidth={true}
                  className={classes.button}
                  onClick={handleDisconnectRequest}
                >
                  Disconnect Device
                </Button>
              </React.Fragment>
            ) : (
              <React.Fragment>
                <form onSubmit={handleSubmit}>
                  <FormControl
                    component="fieldset"
                    disabled={configuring || props.isConnected}
                    error={error}
                    className={classes.formControl}
                  >
                    <div>
                      <FormLabel component="legend">Device Mode:</FormLabel>
                      <RadioGroup
                        aria-label="mode"
                        name="Streaming Source"
                        value={mode}
                        onChange={handleModeChange}
                        row
                      >
                        <FormControlLabel
                          value="DATA_CAPTURE"
                          control={<Radio />}
                          label="Data Capture"
                        />
                        <FormControlLabel
                          value="RECOGNITION"
                          control={<Radio />}
                          label="Recognition"
                        />
                      </RadioGroup>
                    </div>
                    <div className={classes.section1}></div>
                    <div>
                      <FormLabel>Connection Type</FormLabel>
                      <RadioGroup
                        aria-label="source"
                        value={source}
                        onChange={handleSourceChange}
                        row
                      >
                        <FormControlLabel
                          value="SERIAL"
                          control={<Radio />}
                          label="Serial"
                        />
                        <FormControlLabel
                          value="BLE"
                          control={<Radio />}
                          label="BLE"
                        />
                        <FormControlLabel
                          value="TCPIP"
                          control={<Radio />}
                          label="TCP/IP"
                        />
                        <FormControlLabel
                          value="TEST"
                          control={<Radio />}
                          label="Test"
                        />
                        <FormControlLabel
                          value="MICROPHONE"
                          control={<Radio />}
                          label="Microphone"
                        />
                      </RadioGroup>
                    </div>


                    <Scan
                      source={source}
                      handleRowSelection={handleRowSelection}
                      configuring={configuring}
                    />

                    <div className={classes.section1}></div>

                    <div>
                      <FormLabel component="legend">Device ID:</FormLabel>
                      <TextField
                        id="outlined-basic"
                        variant="outlined"
                        value={deviceID}
                        onChange={handleDeviceIDChange}
                        fullWidth={true}
                      />
                    </div>

                    <div className={classes.section1}></div>

                    {source === "SERIAL" ? (
                      <div>
                        <FormLabel component="legend">Baud Rate:</FormLabel>
                        <TextField
                          id="outlined-basic"
                          variant="outlined"
                          value={props.baudRate}
                          onChange={handleDeviceBaudRate}
                          fullWidth={true}
                        />
                      </div>
                    ) : (
                      <div />
                    )}

                    {(source === "MICROPHONE" && mode === "DATA_CAPTURE" ) ? (
                      <div>
                        <FormLabel>Microphone Sample Rate (Hz)</FormLabel>
                        <RadioGroup
                          aria-label="sample_rate"
                          value={sample_rate}
                          defaultValue="16000"
                          onChange={handleSampleRate}
                          row
                        >
                          <FormControlLabel
                            value="8000"
                            control={<Radio />}
                            label="8000"
                          />
                          <FormControlLabel
                            value="11025"
                            control={<Radio />}
                            label="11025"
                          />
                          <FormControlLabel
                            value="16000"
                            control={<Radio />}
                            label="16000"
                          />
                          <FormControlLabel
                            value="22050"
                            control={<Radio />}
                            label="22050"
                          />
                          <FormControlLabel
                            value="44100"
                            control={<Radio />}
                            label="44100"
                          />
                          <FormControlLabel
                            value="48000"
                            control={<Radio />}
                            label="48000"
                          />
                        </RadioGroup>
                      </div>
                    ) : (
                      <div />
                    )}

                    <div className={classes.section1}></div>
                    <div>
                      <Grid container columns spacing={2}>
                        <Grid item xs={12}>
                          <Button
                            type="submit"
                            variant="contained"
                            color="primary"
                            disabled={configuring}
                            fullWidth={true}
                            className={classes.button}
                          >
                            Connect to Device
                          </Button>
                        </Grid>
                      </Grid>
                    </div>
                    <div className={classes.section1}></div>
                    <Typography> {helperText}</Typography>
                  </FormControl>
                </form>
              </React.Fragment>
            )}
          </CardContent>
        </Card>
      </Grid>
      <Grid item>
        <Card className={classes.divWrapper}>
          <CardContent>
            <WebCamera
              setIsCameraConnected={props.setIsCameraConnected}
              isCameraConnected={props.isCameraConnected}
            />
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
};

export default Configure;
