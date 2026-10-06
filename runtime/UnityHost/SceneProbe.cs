using System;
using System.Collections.Generic;
using System.Collections;
using System.IO;
using UnityEngine;
using UnityEngine.Rendering;

// Diagnostic rendering only. No recovered gameplay methods are implemented here.
public sealed class SceneProbe : MonoBehaviour
{
    public Material diagnosticMaterial;
    public Font labelFont;
    [Serializable] public sealed class Node
    {
        public int id, parent;
        public string name, mesh;
        public bool active, render;
        public Vector3 position, scale;
        public Quaternion rotation;
    }
    [Serializable] public sealed class Submesh { public int[] indices; }
    [Serializable] public sealed class Geometry { public string key; public float[] vertices, normals; public Submesh[] submeshes; }
    [Serializable] public sealed class Document { public Node[] nodes; public Geometry[] meshes; }

    private void Awake()
    {
        Application.logMessageReceived += RecordLog;
        File.WriteAllText(Path.Combine(Application.persistentDataPath, "geometry-startup.log"), "SceneProbe Awake\n");
        try { BuildGeometry(); }
        catch (Exception error) { Debug.LogException(error); }
    }

    private void RecordLog(string message, string stack, LogType type)
    {
        File.AppendAllText(Path.Combine(Application.persistentDataPath, "geometry-startup.log"), type + ": " + message + "\n" + stack + "\n");
    }

    private void BuildGeometry()
    {
        var text = Resources.Load<TextAsset>("diagnostic");
        if (text == null) throw new InvalidOperationException("Missing diagnostic geometry");
        var document = JsonUtility.FromJson<Document>(text.text);
        var meshes = new Dictionary<string, Mesh>();
        foreach (var geometry in document.meshes)
        {
            var vertices = new Vector3[geometry.vertices.Length / 3];
            for (int i = 0; i < vertices.Length; ++i)
                vertices[i] = new Vector3(geometry.vertices[i * 3], geometry.vertices[i * 3 + 1], geometry.vertices[i * 3 + 2]);
            var mesh = new Mesh { name = geometry.key, indexFormat = IndexFormat.UInt32, vertices = vertices };
            mesh.subMeshCount = geometry.submeshes.Length;
            for (int i = 0; i < geometry.submeshes.Length; ++i) mesh.SetTriangles(geometry.submeshes[i].indices, i);
            if (geometry.normals != null && geometry.normals.Length == geometry.vertices.Length)
            {
                var normals = new Vector3[vertices.Length];
                for (int i = 0; i < normals.Length; ++i)
                    normals[i] = new Vector3(geometry.normals[i * 3], geometry.normals[i * 3 + 1], geometry.normals[i * 3 + 2]);
                mesh.normals = normals;
            }
            else mesh.RecalculateNormals();
            mesh.RecalculateBounds();
            meshes.Add(geometry.key, mesh);
        }
        var nodes = new Dictionary<int, GameObject>();
        if (diagnosticMaterial == null) throw new InvalidOperationException("Missing diagnostic material");
        var material = diagnosticMaterial;
        Debug.Log("Diagnostic material color: " + material.color.ToString("F5"));
        foreach (var node in document.nodes) nodes.Add(node.id, new GameObject(node.name));
        var sampleRecorded = false;
        foreach (var node in document.nodes)
        {
            var item = nodes[node.id];
            item.transform.SetParent(node.parent == -1 ? transform : nodes[node.parent].transform, false);
            item.transform.localPosition = node.position;
            item.transform.localRotation = node.rotation;
            item.transform.localScale = node.scale;
            if (!sampleRecorded && node.render && !String.IsNullOrEmpty(node.mesh))
            {
                sampleRecorded = true;
                Debug.Log("Transform sample: DTO position " + node.position.ToString("F5") + "; rotation " + node.rotation.ToString("F5") + "; scale " + node.scale.ToString("F5") + "; native position " + item.transform.localPosition.ToString("F5") + "; world position " + item.transform.position.ToString("F5"));
            }
            if (!String.IsNullOrEmpty(node.mesh) && node.render)
            {
                var mesh = meshes[node.mesh];
                item.AddComponent<MeshFilter>().sharedMesh = mesh;
                var renderer = item.AddComponent<MeshRenderer>();
                var materials = new Material[mesh.subMeshCount];
                for (int i = 0; i < materials.Length; ++i) materials[i] = material;
                renderer.sharedMaterials = materials;
            }
            item.SetActive(node.active);
        }
        // Original game scripts activate these initially dormant scene groups.
        // The diagnostic enables only mesh-bearing nodes and their ancestry.
        // This is a viewing policy, not recovered activation/gameplay behavior.
        foreach (var node in document.nodes)
        {
            if (String.IsNullOrEmpty(node.mesh) || !node.render) continue;
            var current = nodes[node.id].transform;
            while (current != transform)
            {
                current.gameObject.SetActive(true);
                current = current.parent;
            }
        }
        var renderers = GetComponentsInChildren<MeshRenderer>();
        if (renderers.Length == 0) throw new InvalidOperationException("Recovered geometry has no active renderers");
        var first = true;
        var bounds = new Bounds();
        foreach (var renderer in renderers)
        {
            foreach (var vertex in renderer.GetComponent<MeshFilter>().sharedMesh.vertices)
            {
                var world = renderer.transform.TransformPoint(vertex);
                if (first) { bounds = new Bounds(world, Vector3.zero); first = false; }
                else bounds.Encapsulate(world);
            }
        }
        var camera = new GameObject("Diagnostic camera").AddComponent<Camera>();
        camera.transform.rotation = Quaternion.Euler(45, 35, 0);
        var distance = Mathf.Max(bounds.size.magnitude, 1);
        camera.transform.position = bounds.center - camera.transform.forward * distance;
        camera.orthographic = true;
        camera.orthographicSize = distance * 0.55f;
        camera.clearFlags = CameraClearFlags.SolidColor;
        camera.allowHDR = false;
        camera.allowMSAA = false;
        camera.farClipPlane = distance * 4;
        camera.backgroundColor = new Color(0.05f, 0.06f, 0.09f);
        Debug.Log("Camera background " + camera.backgroundColor.ToString("F5") + "; position " + camera.transform.position.ToString("F5") + "; size " + camera.orthographicSize);
        var light = new GameObject("Diagnostic light").AddComponent<Light>();
        light.type = LightType.Directional;
        light.intensity = 1.2f;
        light.transform.rotation = Quaternion.Euler(50, -30, 0);
        RenderSettings.ambientMode = AmbientMode.Flat;
        RenderSettings.ambientLight = new Color(0.55f, 0.55f, 0.55f);
        Application.targetFrameRate = 30;
        Debug.Log("Recovered geometry diagnostic started: " + renderers.Length + " active mesh renderers");
        Debug.Log("Viewport: " + Screen.width + "x" + Screen.height + "; camera aspect " + camera.aspect + "; bounds " + bounds);
        StartCoroutine(CaptureDiagnosticFrame());
    }

    private IEnumerator CaptureDiagnosticFrame()
    {
        while (!SplashScreen.isFinished) yield return null;
        yield return new WaitForSecondsRealtime(0.5f);
        yield return new WaitForEndOfFrame();
        var frame = ScreenCapture.CaptureScreenshotAsTexture();
        try { File.WriteAllBytes(Path.Combine(Application.persistentDataPath, "geometry-frame.png"), frame.EncodeToPNG()); }
        finally { Destroy(frame); }
        Debug.Log("Diagnostic frame captured");
    }

    private void OnGUI()
    {
        var style = new GUIStyle(GUI.skin.label) { font = labelFont, fontSize = 24, wordWrap = true };
        style.normal.textColor = Color.white;
        GUI.Label(new Rect(24, 24, Screen.width - 48, 80), "Recovered geometry diagnostic\nNeutral materials; gameplay pending", style);
    }
}
