using System;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

public static class BuildProbe
{
    public static void ExportIOS()
    {
        if (Application.unityVersion != "2020.3.12f1") throw new InvalidOperationException("Expected Unity 2020.3.12f1");
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        if (Environment.GetEnvironmentVariable("DISCO_EMPTY_HOST") != "1")
        {
            var probe = new GameObject("Recovered geometry diagnostic").AddComponent<SceneProbe>();
            var shader = Shader.Find("Legacy Shaders/Diffuse");
            if (shader == null) throw new InvalidOperationException("Missing built-in diagnostic shader");
            const string materialPath = "Assets/Resources/DiagnosticMaterial.mat";
            AssetDatabase.DeleteAsset(materialPath);
            var material = new Material(shader) { color = new Color(0.65f, 0.68f, 0.73f) };
            if (!material.HasProperty("_Color")) throw new InvalidOperationException("Diagnostic shader must support color tint");
            AssetDatabase.CreateAsset(material, materialPath);
            probe.diagnosticMaterial = material;
            probe.labelFont = Resources.GetBuiltinResource<Font>("Arial.ttf");
        }
        EditorSceneManager.SaveScene(scene, "Assets/Diagnostic.unity");
        PlayerSettings.productName = "Disco Geometry Lab";
        PlayerSettings.companyName = "Disco Port";
        PlayerSettings.SetApplicationIdentifier(BuildTargetGroup.iOS, "org.discoport.unityprobe");
        PlayerSettings.SetScriptingBackend(BuildTargetGroup.iOS, ScriptingImplementation.IL2CPP);
        PlayerSettings.SetArchitecture(BuildTargetGroup.iOS, 1);
        PlayerSettings.iOS.targetDevice = iOSTargetDevice.iPadOnly;
        PlayerSettings.iOS.targetOSVersionString = "17.0";
        PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.iOS, false);
        PlayerSettings.SetGraphicsAPIs(BuildTarget.iOS, new[] { GraphicsDeviceType.Metal });
        PlayerSettings.defaultInterfaceOrientation = UIOrientation.LandscapeLeft;
        PlayerSettings.iOS.appleEnableAutomaticSigning = true;
        var team = Environment.GetEnvironmentVariable("UNITY_DEVELOPMENT_TEAM");
        if (!String.IsNullOrEmpty(team)) PlayerSettings.iOS.appleDeveloperTeamID = team;
        var output = Environment.GetEnvironmentVariable("UNITY_IOS_OUTPUT");
        if (String.IsNullOrEmpty(output)) throw new InvalidOperationException("UNITY_IOS_OUTPUT must point under artifacts");
        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions {
            scenes = new[] { "Assets/Diagnostic.unity" }, locationPathName = output,
            target = BuildTarget.iOS, options = BuildOptions.Development
        });
        if (report.summary.result != BuildResult.Succeeded) throw new InvalidOperationException("Unity iOS export failed: " + report.summary.result);
        Debug.Log("Unity iOS diagnostic export succeeded");
    }
}
