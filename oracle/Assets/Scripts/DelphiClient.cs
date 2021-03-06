﻿using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;
using UnityEngine.Assertions;
using SimpleJSON;

/// <summary>
/// Client used to communicate with Delphi.
/// </summary>
public class DelphiClient : MonoBehaviour
{
    /// <summary>
    /// Base URL of all of Delphi's endpoints.
    /// </summary>
    private static readonly string BASE_URL = Config.cfg["delphi client"]["base-url"].StringValue;

    /// <summary>
    /// Delphi's update constraint endpoint.
    /// </summary>
    private static readonly string UPDATE_CONSTRAINT_ENDPOINT = Config.cfg["delphi client"]["update-constraint-endpoint"].StringValue;

    /// <summary>
    /// Delphi's get data endpoint.
    /// </summary>
    private static readonly string GET_DATA_ENDPOINT = Config.cfg["delphi client"]["get-data-endpoint"].StringValue;

    /// <summary>
    /// Sets the delay at which the UpdateNodes is called in seconds.
    /// </summary>
    [SerializeField]
    private static float DELAY_UPDATE_TIME = 0.0f;

    /// <summary>
    /// Sets the interval at which the UpdateNodes is called in seconds.
    /// </summary>
    [SerializeField]
    private static float UPDATE_INTERVAL_TIME = 0.5f;

    /// <summary>
    /// A list of the current paths from delphi.
    /// </summary>
    private List<List<string>> currentPaths;

    public List<List<string>> CurrentPaths
    {
        get { return currentPaths; }
    }

    [SerializeField]
    private PathManager pathManager = null;

    /// <summary>
    /// The current game's <code>UIManager</code>. This is used to grab the current floor.
    /// <see cref="UIManager"/>
    /// </summary>
    private UIManager ui;

    void Start()
    {
        currentPaths = new List<List<string>>();
        ui = GameObject.Find("EventSystem").GetComponent<UIManager>();
        Assert.IsNotNull(ui);
        Assert.IsNotNull(pathManager);
        InvokeRepeating("GetData", DELAY_UPDATE_TIME, UPDATE_INTERVAL_TIME);
    }

    /// <summary>
    /// Updates all of the fields for each of the GraphComponents supplied.
    /// <param name="node">The graph component to toggle status</param>
    /// </summary>
    public void ToggleNodeStatus(GraphComponentStatus node)
    {
        StartCoroutine(ToggleStatus(node));
    }

    /// <summary>
    /// Updates the status of the node associated with the given id.
    /// <param name="node">The graph component to toggle status</param>
    /// </summary>
    private IEnumerator ToggleStatus(GraphComponentStatus node)
    {
        JSONObject requestData = new JSONObject();
        requestData.Add("node_id", node.Id);

        return PostJson(BASE_URL + UPDATE_CONSTRAINT_ENDPOINT, requestData);
    }

    /// <summary>
    /// Continiously called to fetch data from Delphi.
    /// Updates according to the value of the <code>UPDATE_INTERVAL_TIME</code> property.
    /// <see cref="UPDATE_INTERVAL_TIME"/>
    /// </summary>
    private void GetData()
    {
        StartCoroutine(GetDelphiData(BASE_URL + GET_DATA_ENDPOINT));
    }

    /// <summary>
    /// Calls a post request to the given uri with the given json.
    /// <param name="uri">The uri to send the request to</param>
    /// <param name="json">The json to put into the body of the request</param>
    /// </summary>
    private IEnumerator PostJson(string uri, JSONObject json) 
    {
        // Cannot using UnityWebRequest.Post because it will URL encode the JSON.
        using(UnityWebRequest www = new UnityWebRequest(uri, UnityWebRequest.kHttpVerbPOST))
        {
            www.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(json.ToString()));
            www.SetRequestHeader("Content-Type", "application/json");

            yield return www.SendWebRequest();

            if(www.isNetworkError || www.isHttpError)
            {
                Debug.LogError(www.error);
            }

            yield break;
        }
    }

    /// <summary>
    /// Calls a get request to gather data from Delphi.
    /// <param name="uri">The uri to send the request to</param>
    /// </summary>
    private IEnumerator GetDelphiData(string uri)
    {
        using(UnityWebRequest www = UnityWebRequest.Get(uri))
        {
            www.SetRequestHeader("Content-Type", "application/json");
            yield return www.SendWebRequest();

            if(www.isNetworkError || www.isHttpError)
            {
                Debug.LogError(www.error);
            }
            else
            {
                var json = JSON.Parse(www.downloadHandler.text).AsObject;
                Debug.Log(json);

                // Once we get the keywords figured out, this is where we will update the nodes on the currently selected floor.

                // Update the statuses of all the graph components on this floor
                if(json["statuses"] != null)
                {
                    foreach(var status in json["statuses"])
                    {
                        var component = ui.CurrentFloor.GetGraphComponentByID(status.Key) as GraphComponentStatus;
                        if(component != null)
                        {
                            component.Status = status.Value;
                        }
                    }
                }

                // Update the room counts on this floor
                if(json["Counts"] != null)
                {
                    foreach(var count in json["Counts"])
                    {
                        var component = ui.CurrentFloor.GetGraphComponentByID(count.Key) as Room;
                        if(component != null)
                        {
                            component.PeopleCount = count.Value;
                        }
                    }
                }
                
                // Update the current paths available
                if(json["paths"] != null)
                {
                    currentPaths.Clear();
                    foreach(var path in json["paths"])
                    {
                        var newPath = new List<string>();
                        foreach(var node in path.Value)
                        {
                            newPath.Add(node.Value);
                        }
                        currentPaths.Add(newPath);
                        pathManager.PathUpdate(newPath);
                    }
                }
            }

            yield break;
        }
    }
}